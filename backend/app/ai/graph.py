from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek
import logging

from app.core.config import settings
from app.ai.state import AgentState
from app.ai.tools import llm_classifier, classify_intent, build_tools
from app.ai.guard import execute_security_guard

logger = logging.getLogger(__name__)

llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.3,
    streaming=True,
)


async def process_input_node(state: AgentState):
    """预处理：不做额外处理，透传给分类器"""
    return state


def classify_node(state: AgentState):
    """意图分类路由节点"""
    return state


async def chat_node(state: AgentState):
    """闲聊回复"""
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""
    try:
        resp = await llm.ainvoke([SystemMessage(content="你是智宿云酒店的AI虚拟管家，友好、专业、简洁地回复住客。"), *state["messages"]])
        state["messages"].append(resp)
    except Exception:
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content="抱歉，系统暂时无法回复，请稍后再试或联系前台。"))
    state["business_cards"] = []
    return state


async def knowledge_node(state: AgentState):
    """知识库检索回复"""
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""

    try:
        from app.ai.rag import query_vector_store
        docs = await query_vector_store(user_text)
        context = "\n".join(docs) if docs else "知识库无匹配信息"

        prompt = (
            "你是智宿云酒店的AI虚拟管家。请严格依据以下酒店知识库信息回答住客问题。"
            "如果知识库没有相关信息，请诚实告知住客并建议联系前台。\n\n"
            f"【酒店知识库】\n{context}\n\n"
            f"【住客问题】{user_text}"
        )
        resp = await llm.ainvoke(prompt)
        state["messages"].append(resp)
    except Exception as e:
        logger.error(f"knowledge_node RAG查询失败: {type(e).__name__}: {e}")
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content="抱歉，知识库暂时无法检索，请联系前台获取帮助。"))
    state["business_cards"] = []
    return state


async def action_node(state: AgentState):
    """Tool Calling 执行节点"""
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""
    print(f"[GRAPH-PRINT] action_node 进入, user_text={user_text[:50]}", flush=True)

    cards = []
    try:
        tools = build_tools()
        llm_with_tools = llm.bind_tools(tools)

        from langchain_core.messages import HumanMessage, SystemMessage
        system_msg = SystemMessage(content=(
            "你是智宿云酒店的AI虚拟管家。当前住客需要你执行具体操作。\n"
            "你必须调用工具来完成请求，禁止只回复文字而不调用工具。\n\n"
            "可用工具：\n"
            "- control_device_tool: 控制灯光/窗帘/空调\n"
            "- create_work_order_tool: 创建送物或报修工单\n"
            "- query_knowledge_tool: 检索酒店知识库\n"
            "- modify_room_price_tool: 修改房价（仅店长可用）\n\n"
            "根据住客请求选择合适的工具并立即执行。"
        ))
        resp = await llm_with_tools.ainvoke([system_msg, HumanMessage(content=user_text)])

        if resp.tool_calls:
            for call in resp.tool_calls:
                tool_name = call["name"]
                tool_args = call["args"]

                # 安全拦截
                guard_result = await execute_security_guard(tool_name, state["role"], tool_args, user_text, user_id=state.get("user_id", ""))
                if not guard_result["ok"]:
                    cards.append({"type": "error", "title": guard_result["error"]})
                    continue

                # 从 state 注入 room_id（杜绝LLM幻觉）
                if tool_name == "control_device_tool" and state.get("room_id"):
                    tool_args["room_id"] = state["room_id"]
                if tool_name == "create_work_order_tool" and state.get("room_id"):
                    tool_args["room_id"] = state["room_id"]

                # 执行工具
                for t in tools:
                    if t.name == tool_name:
                        result = await t.ainvoke(tool_args)
                        card_title = (
                            "🔧 空调调节中" if tool_name == "control_device_tool"
                            else "📦 报修工单已创建" if tool_name == "create_work_order_tool"
                            else "📚 知识库检索" if tool_name == "query_knowledge_tool"
                            else f"已执行：{tool_name}"
                        )
                        cards.append({"type": "success", "title": card_title, "detail": str(result)})

                        # 工单创建成功后广播 WebSocket 通知前台
                        if tool_name == "create_work_order_tool" and "工单已创建" in str(result):
                            try:
                                import re as _re
                                from app.ws.manager import manager as ws_manager
                                from app.core.database import async_session
                                from sqlmodel import select as _select
                                from app.models.room import Room as _Room
                                import uuid as _uuid
                                async with async_session() as _db:
                                    room_res = await _db.execute(_select(_Room.room_number).where(_Room.id == _uuid.UUID(tool_args["room_id"])))
                                    room_number = room_res.scalar_one_or_none() or "未知"
                                _order_id_match = _re.search(r"\[order_id=([^\]]+)\]", str(result))
                                _order_id = _order_id_match.group(1) if _order_id_match else ""
                                await ws_manager.broadcast_biz({
                                    "event": "work_order.new",
                                    "data": {
                                        "order_id": _order_id,
                                        "room_number": room_number,
                                        "type": tool_args.get("type", "repair"),
                                        "content": tool_args.get("content", ""),
                                    },
                                })
                                print("[WS-PRINT] 广播完成", flush=True)
                            except Exception as e:
                                print(f"[WS-PRINT] 广播失败: {type(e).__name__}: {e}", flush=True)
                        break

        # 兜底：LLM 没调用任何 tool 时，根据关键词强制执行
        if not cards:
            text = user_text.lower()
            wo_type = None
            if any(kw in text for kw in ["报修", "维修", "坏了", "故障", "堵了", "漏水", "不制冷", "不工作", "工单"]):
                wo_type = "repair"
            elif any(kw in text for kw in ["送", "拿", "要", "需要"]):
                wo_type = "delivery"

            if wo_type:
                wo_args = {"type": wo_type, "content": user_text, "room_id": state.get("room_id", "")}
                guard = await execute_security_guard("create_work_order_tool", state["role"], wo_args, user_text, user_id=state.get("user_id", ""))
                if guard["ok"]:
                    for t in tools:
                        if t.name == "create_work_order_tool":
                            result = await t.ainvoke(wo_args)
                            label = "📦 报修工单已创建" if wo_type == "repair" else "📦 送物工单已创建"
                            cards.append({"type": "success", "title": label, "detail": str(result)})
                            # 广播 WebSocket 通知前台
                            try:
                                from app.ws.manager import manager as ws_manager
                                from app.core.database import async_session
                                from sqlmodel import select as _select
                                from app.models.room import Room as _Room
                                import uuid as _uuid
                                async with async_session() as _db:
                                    room_res = await _db.execute(_select(_Room.room_number).where(_Room.id == _uuid.UUID(wo_args["room_id"])))
                                    room_number = room_res.scalar_one_or_none() or "未知"
                                await ws_manager.broadcast_biz({
                                    "event": "work_order.new",
                                    "data": {
                                        "room_number": room_number,
                                        "type": wo_type,
                                        "content": user_text,
                                    },
                                })
                                print("[WS-PRINT] 兜底广播完成", flush=True)
                            except Exception as e:
                                print(f"[WS-PRINT] 兜底广播失败: {type(e).__name__}: {e}", flush=True)
                            break

        state["messages"].append(resp)
    except Exception as e:
        import traceback
        traceback.print_exc()
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content="抱歉，操作执行失败，请联系前台处理。"))
    state["business_cards"] = cards
    return state


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("process_input", process_input_node)
    workflow.add_node("classify", classify_node)
    workflow.add_node("chat_response", chat_node)
    workflow.add_node("knowledge_response", knowledge_node)
    workflow.add_node("action_response", action_node)

    workflow.add_edge(START, "process_input")

    # 条件路由：语义分类
    async def route_by_intent(state: AgentState):
        last_msg = state["messages"][-1] if state["messages"] else None
        user_text = last_msg.content if last_msg else ""
        intent = await classify_intent(user_text)
        state["intent"] = intent
        print(f"[GRAPH-PRINT] route_by_intent: '{user_text[:30]}' → {intent}", flush=True)
        return intent

    workflow.add_conditional_edges(
        "process_input",
        route_by_intent,
        {
            "chat": "chat_response",
            "knowledge": "knowledge_response",
            "action": "action_response",
        },
    )

    workflow.add_edge("chat_response", END)
    workflow.add_edge("knowledge_response", END)
    workflow.add_edge("action_response", END)

    return workflow.compile(checkpointer=MemorySaver())
