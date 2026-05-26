import uuid
from datetime import datetime, timezone
from typing import Any
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from sqlmodel import select, func, update

from app.core.config import settings
from app.core.database import async_session
from app.models.work_order import WorkOrder
from app.models.room import Room

llm_classifier = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0,
)


async def classify_intent(user_input: str) -> str:
    """语义分析：让 LLM 判断用户意图，返回 chat / knowledge / action"""
    prompt = (
        "你是酒店AI管家的意图分类器。分析住客输入，严格输出以下三者之一：\n"
        "- chat: 普通闲聊、打招呼、天气等与酒店业务无关的对话\n"
        "- knowledge: 询问酒店设施、服务、价格、时间、政策等信息\n"
        "- action: 要求控制房间设备（灯光/窗帘/空调）或请求送物/报修等服务\n\n"
        f"住客输入：{user_input}\n\n"
        "只输出一个词（chat / knowledge / action），不要任何解释："
    )
    resp = await llm_classifier.ainvoke(prompt)
    result = resp.content.strip().lower()
    if result in ("chat", "knowledge", "action"):
        return result
    return "chat"


# ── Tool 1: 控制设备 ──
@tool
async def control_device_tool(device: str, value: Any, room_id: str = "") -> str:
    """
    控制客房设备（灯光、窗帘、空调）。
    device: living_light / bedroom_light / bedside_light / curtain / ac_temp / ac_mode
    value: 灯光用 bool，窗帘/温度用 int，ac_mode 用 str("cool"/"heat")
    room_id: 由系统自动注入，勿手动填写
    """
    if device == "ac_temp" and isinstance(value, (int, float)):
        value = max(16, min(30, int(value)))
    if not room_id:
        return "错误：缺少 room_id，无法控制设备"
    async with async_session() as db:
        room = await db.get(Room, uuid.UUID(room_id))
        if not room:
            return f"错误：未找到房间 {room_id}"
        states = room.device_states or {}
        states[device] = value
        await db.execute(
            update(Room).where(Room.id == room.id).values(device_states=states)
        )
        await db.commit()
    return f"已执行设备控制：{device} → {value}"


# ── Tool 2: 创建工单 ──
@tool
async def create_work_order_tool(type: str, content: str, room_id: str = "") -> str:
    """
    创建酒店服务工单（送物 delivery / 报修 repair）。
    room_id: 由系统自动注入，勿手动填写
    """
    if not room_id:
        return "错误：缺少 room_id，无法创建工单"
    async with async_session() as db:
        result = await db.execute(
            select(func.count()).where(
                WorkOrder.room_id == uuid.UUID(room_id),
                WorkOrder.status.in_(["submitted", "accepted", "processing"]),
            )
        )
        pending_count = result.scalar() or 0
        if pending_count >= 5:
            return f"安全熔断：该房间未结工单已达 {pending_count} 个上限，请稍后再试"

        wo = WorkOrder(
            room_id=uuid.UUID(room_id),
            type=type,
            content=content,
            status="submitted",
            ai_generated=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(wo)
        await db.commit()
        return f"工单已创建：{type} — {content}"


# ── Tool 3: 知识库检索 ──
@tool
async def query_knowledge_tool(query: str) -> str:
    """
    检索酒店知识库（pgvector RAG），获取酒店服务、设施、政策等信息。
    """
    from app.ai.rag import query_vector_store

    docs = await query_vector_store(query)
    if not docs:
        return "知识库中未找到相关信息"
    return "\n—\n".join(docs)


# ── Tool 4: 修改房价（仅 manager） ──
@tool
def modify_room_price_tool(room_type: str, new_price_yuan: float) -> str:
    """
    修改指定房型的当前价格。仅店长(manager)可调用。
    room_type: big_bed / twin / suite
    new_price_yuan: 新价格（元），涨幅不超过 base_price 的 50%
    """
    return f"调价请求已记录：{room_type} → ¥{new_price_yuan}（待审批）"


# ── Tool 集合 ──
def build_tools():
    return [
        control_device_tool,
        create_work_order_tool,
        query_knowledge_tool,
        modify_room_price_tool,
    ]
