import uuid
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from langchain_core.messages import HumanMessage, AIMessage
from app.core.utils import cst_now, cst_isoformat

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.guest import Guest
from app.models.user import Staff
from app.models.order import Order
from app.models.room import Room
from app.models.chat import ChatSession, ChatMessage
from app.models.ai_log import AIPricingLog
from app.ai.graph import build_graph
from app.ai.state import AgentState
from app.schemas.ai import ChatRequest, SafetyThresholdRequest

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/chat")
async def ai_chat(
    req: ChatRequest,
    current_user: Guest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """SSE 流式对话接口"""
    result = await db.execute(
        select(Order).where(
            Order.user_id == current_user.id, Order.status == "checked_in"
        ).order_by(Order.created_at.desc()).limit(1)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="请先办理入住后再使用AI管家")

    result = await db.execute(select(Room).where(Room.id == order.room_id))
    room = result.scalar_one_or_none()

    user_input = req.message

    # 创建或复用 ChatSession
    result = await db.execute(
        select(ChatSession).where(ChatSession.order_id == order.id, ChatSession.status == "active")
    )
    session = result.scalar_one_or_none()
    if not session:
        session = ChatSession(order_id=order.id, room_id=order.room_id, status="active")
        db.add(session)
        await db.commit()
        await db.refresh(session)

    # 保存用户消息
    user_msg = ChatMessage(session_id=session.id, role="user", content=user_input)
    db.add(user_msg)
    await db.commit()

    graph = build_graph()
    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_input)],
        "user_id": str(current_user.id),
        "room_id": str(order.room_id) if room else None,
        "order_id": str(order.id),
        "role": "guest" if isinstance(current_user, Guest) else current_user.role,
        "intent": "chat",
        "business_cards": [],
    }

    async def event_generator():
        final_text = ""
        final_cards = []
        node_executed = False  # 标记是否已进入实际节点执行（排除分类路由的 LLM 事件）

        try:
            async for event in graph.astream_events(
                initial_state,
                config={"configurable": {"thread_id": str(session.id)}},
                version="v2",
            ):
                kind = event["event"]
                name = event.get("name", "")

                # 节点开始执行 → 后续的 on_chat_model_stream 都来自实际节点
                if kind == "on_chain_start" and name in ("chat_response", "knowledge_response", "action_response"):
                    node_executed = True

                if kind == "on_chat_model_stream" and node_executed:
                    chunk = event["data"]["chunk"]
                    token = chunk.content if hasattr(chunk, "content") and chunk.content else ""
                    if token:
                        final_text += token
                        yield f"data: {json.dumps({'type': 'text', 'content': token}, ensure_ascii=False)}\n\n"

                elif kind == "on_chain_end" and name == "action_response":
                    output = event["data"].get("output", {})
                    cards = output.get("business_cards", [])
                    final_cards = cards
                    for card in cards:
                        yield f"data: {json.dumps({'type': 'card', 'card': card}, ensure_ascii=False)}\n\n"

                # 兜底：从 knowledge_response / chat_response 节点 output 中提取 AI 回复
                elif kind == "on_chain_end" and name in ("knowledge_response", "chat_response"):
                    output = event["data"].get("output", {})
                    messages = output.get("messages", [])
                    # 从后往前找最后一条 AIMessage
                    ai_content = None
                    for msg in reversed(messages):
                        if isinstance(msg, AIMessage) and msg.content:
                            ai_content = msg.content
                            break
                        content = getattr(msg, "content", None)
                        if isinstance(msg, dict) and msg.get("type") == "ai" and content:
                            ai_content = content
                            break
                    if ai_content:
                        final_text = ai_content
                        yield f"data: {json.dumps({'type': 'text', 'content': ai_content}, ensure_ascii=False)}\n\n"

        except Exception as exc:
            yield f"data: {json.dumps({'type': 'text', 'content': f'抱歉，系统暂时无法回答，请联系前台。({exc})'}, ensure_ascii=False)}\n\n"

        # 保存 AI 回复
        ai_msg = ChatMessage(
            session_id=session.id,
            role="assistant",
            content=final_text or "已为您处理请求",
            tool_calls={"cards": final_cards} if final_cards else None,
        )
        db.add(ai_msg)
        await db.commit()

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/chat/{session_id}/history")
async def get_chat_history(
    session_id: str,
    current_user: Guest = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 校验会话属于当前用户
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == uuid.UUID(session_id),
            ChatSession.order_id.in_(
                select(Order.id).where(Order.user_id == current_user.id)
            ),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="会话不属于当前用户")

    result = await db.execute(
        select(ChatMessage).where(ChatMessage.session_id == uuid.UUID(session_id)).order_by(ChatMessage.created_at)
    )
    messages = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "role": m.role,
            "content": m.content,
            "tool_calls": m.tool_calls,
            "created_at": cst_isoformat(m.created_at),
        }
        for m in messages
    ]


@router.get("/pricing/logs")
async def get_pricing_logs(
    current_user: Staff = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AIPricingLog).order_by(AIPricingLog.created_at.desc()).limit(50))
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "room_type": log.room_type,
            "trigger_reason": log.trigger_reason,
            "original_price": log.original_price,
            "suggested_price": log.suggested_price,
            "status": log.status,
            "suggested_by": log.suggested_by,
            "created_at": cst_isoformat(log.created_at),
        }
        for log in logs
    ]


@router.put("/pricing/{log_id}/approve")
async def approve_pricing(
    log_id: str,
    current_user: Staff = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AIPricingLog).where(AIPricingLog.id == uuid.UUID(log_id)))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="定价记录不存在")
    if log.status != "pending":
        raise HTTPException(status_code=409, detail="该定价已处理")

    log.status = "approved"
    log.confirmed_by = current_user.id
    log.decided_at = cst_now()

    from sqlmodel import update
    await db.execute(
        update(Room).where(Room.room_type == log.room_type).values(current_price=log.suggested_price)
    )
    await db.commit()
    return {"message": f"已批准调价，{log.room_type} 价格更新为 {log.suggested_price}"}


@router.put("/pricing/{log_id}/reject")
async def reject_pricing(
    log_id: str,
    current_user: Staff = Depends(require_role("manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AIPricingLog).where(AIPricingLog.id == uuid.UUID(log_id)))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="定价记录不存在")

    log.status = "rejected"
    log.confirmed_by = current_user.id
    log.decided_at = cst_now()
    await db.commit()
    return {"message": "已拒绝调价"}


@router.post("/safety-threshold")
async def set_safety_threshold(
    req: SafetyThresholdRequest,
    current_user: Staff = Depends(require_role("manager")),
):
    """店长设置 AI 定价安全阈值"""
    threshold = req.threshold
    import app.ai.guard as guard
    guard.PRICE_MAX_FACTOR = 1 + max(0, min(100, threshold)) / 100
    return {"message": f"安全阈值已更新为 {threshold}%", "factor": guard.PRICE_MAX_FACTOR}
