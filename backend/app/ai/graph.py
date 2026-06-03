from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langchain_deepseek import ChatDeepSeek
import asyncio
import logging

from app.core.config import settings
from app.ai.state import AgentState
from app.ai.tools import classify_intent, build_tools
from app.ai.guard import execute_security_guard

logger = logging.getLogger(__name__)

llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.3,
    streaming=True,
)


async def chat_node(state: AgentState):
    """闲聊回复"""
    try:
        recent = state["messages"][-10:]
        user_count = sum(1 for m in recent if hasattr(m, "type") and m.type == "human")
        system_msg = SystemMessage(content=(
            "你是智宿云酒店的AI虚拟管家，友好、专业、简洁地回复住客。\n"
            "请根据上下文理解住客的问题并准确回答。不要重复住客的话。\n"
            f"当前对话中住客已发送 {user_count} 条消息。"
        ))
        resp = await llm.ainvoke([system_msg, *recent])
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

        recent = state["messages"][-5:]
        recent_text = "\n".join(f"{m.type}: {m.content}" for m in recent if hasattr(m, "content") and m.content)
        system_prompt = (
            "你是智宿云酒店的AI虚拟管家。请严格依据以下酒店知识库信息回答住客问题。"
            "如果知识库没有相关信息，请诚实告知住客并建议联系前台。\n\n"
            f"【酒店知识库】\n{context}\n\n"
            f"【最近对话】\n{recent_text}"
        )
        from langchain_core.messages import HumanMessage
        resp = await llm.ainvoke([SystemMessage(content=system_prompt), HumanMessage(content=user_text)])
        state["messages"].append(resp)
    except Exception as e:
        logger.error(f"knowledge_node RAG查询失败: {type(e).__name__}: {e}")
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content="抱歉，知识库暂时无法检索，请联系前台获取帮助。"))
    state["business_cards"] = []
    return state


def _get_card_title(tool_name: str, tool_args: dict = None) -> str:
    if tool_name == "control_device_tool":
        device = (tool_args or {}).get("device", "")
        device_names = {
            "living_light": "客厅灯光", "bedroom_light": "卧室灯光",
            "bedside_light": "床头灯", "curtain": "窗帘",
            "ac_temp": "空调温度", "ac_mode": "空调模式",
        }
        name = device_names.get(device, "设备")
        return f"✅ {name}已调节"
    if tool_name == "create_work_order_tool":
        return "📦 工单已创建"
    if tool_name == "query_knowledge_tool":
        return "📚 知识库检索"
    return f"✅ {tool_name}已执行"


async def _broadcast_work_order(tool_args: dict, result: str):
    """Broadcast work order creation via WebSocket."""
    if "工单已创建" not in str(result):
        return
    try:
        import re
        from app.ws.manager import manager as ws_manager
        from app.core.database import async_session
        from sqlmodel import select
        from app.models.room import Room
        import uuid as _uuid

        room_id = tool_args.get("room_id", "")
        if not room_id:
            return

        async with async_session() as db:
            room_res = await db.execute(select(Room.room_number).where(Room.id == _uuid.UUID(room_id)))
            room_number = room_res.scalar_one_or_none() or "未知"

        order_id_match = re.search(r"\[order_id=([^\]]+)\]", str(result))
        order_id = order_id_match.group(1) if order_id_match else ""

        await ws_manager.broadcast_biz({
            "event": "work_order.new",
            "data": {
                "order_id": order_id,
                "room_number": room_number,
                "type": tool_args.get("type", "repair"),
                "content": tool_args.get("content", ""),
            },
        })
    except Exception as e:
        logger.warning(f"WS broadcast failed: {e}")


async def _execute_single_tool(call, tools, state, user_text):
    """Execute a single tool call, return card and optional tool message."""
    tool_name = call["name"]
    tool_args = dict(call["args"])  # copy to avoid mutating original

    guard_result = await execute_security_guard(
        tool_name, state["role"], tool_args, user_text, user_id=state.get("user_id", "")
    )
    if not guard_result["ok"]:
        return {"card": {"type": "error", "title": guard_result["error"]}, "tool_message": None}

    # Inject room_id from state (not from LLM)
    if tool_name in ("control_device_tool", "create_work_order_tool") and state.get("room_id"):
        tool_args["room_id"] = state["room_id"]

    for t in tools:
        if t.name == tool_name:
            result = await t.ainvoke(tool_args)
            card_title = _get_card_title(tool_name, tool_args)
            return {
                "card": {"type": "success", "title": card_title, "detail": str(result)},
                "tool_message": (call.get("id", ""), str(result)),
            }

    return {"card": {"type": "error", "title": f"未知工具：{tool_name}"}, "tool_message": None}


MAX_ITERATIONS = 5


async def action_node(state: AgentState):
    """Tool Calling with multi-step agent loop."""
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""
    # 去掉用户输入中的房间号，防止 LLM 控制别的房间
    import re
    clean_text = re.sub(r'\d{3,4}号?房?间?|room\s*\d+', '', user_text).strip()
    if not clean_text:
        clean_text = user_text
    logger.info(f"action_node entered, user_text={clean_text[:50]}")

    cards = []
    try:
        tools = build_tools()
        llm_with_tools = llm.bind_tools(tools)

        system_msg = SystemMessage(content=(
            "你是智宿云酒店的AI虚拟管家。当前住客需要你执行具体操作。\n"
            "请根据住客请求选择合适的工具执行。如果没有匹配的工具，直接回复文字说明。\n\n"
            "可用工具：\n"
            "- control_device_tool: 控制灯光/窗帘/空调\n"
            "- create_work_order_tool: 创建送物或报修工单\n"
            "- query_knowledge_tool: 检索酒店知识库\n"
            "- modify_room_price_tool: 修改房价（仅店长可用）\n\n"
            "⚠️ room_id 由系统自动注入，不要在工具调用中指定 room_id 参数！\n"
            "即使住客提到房间号（如「202房间」），也不要传 room_id，系统会自动处理。\n\n"
            "重要规则：\n"
            "- 如果住客同时提出多个操作请求（如「空调调到20度并且把窗帘关闭」），必须返回多个tool_calls，每个操作一个tool_call\n"
            "- 每个tool_call对应一个独立的操作，不要合并\n\n"
            "设备参数严格对照表：\n"
            "| 设备 | device值 | value类型 | 示例 |\n"
            "| 客厅灯 | living_light | bool | true=开, false=关 |\n"
            "| 卧室灯 | bedroom_light | bool | true=开, false=关 |\n"
            "| 床头灯 | bedside_light | bool | true=开, false=关 |\n"
            "| 窗帘 | curtain | int | 0=全关, 100=全开, 50=半开 |\n"
            "| 空调温度 | ac_temp | int | 16-30 |\n"
            "| 空调模式 | ac_mode | str | \"cool\"或\"heat\" |\n\n"
            "⚠️ 窗帘必须用int，不能用bool！「开窗帘」= curtain=100，「关窗帘」= curtain=0\n\n"
            "根据住客请求选择合适的工具并立即执行。"
        ))

        messages = [system_msg, HumanMessage(content=clean_text)]

        for iteration in range(MAX_ITERATIONS):
            resp = await llm_with_tools.ainvoke(messages)

            if not resp.tool_calls:
                # LLM done calling tools
                if resp.content:
                    messages.append(resp)
                break

            # Execute all tool calls in parallel
            results = await asyncio.gather(*[
                _execute_single_tool(call, tools, state, user_text)
                for call in resp.tool_calls
            ])

            # Feed results back to LLM (ToolMessages are local, not stored in state)
            messages.append(resp)  # assistant message with tool_calls
            for call, result in zip(resp.tool_calls, results):
                cards.append(result["card"])
                if result["tool_message"]:
                    call_id, detail = result["tool_message"]
                    messages.append(ToolMessage(content=detail, tool_call_id=call_id))
                    await _broadcast_work_order(call["args"], detail)
        else:
            # MAX_ITERATIONS reached without LLM stopping
            logger.warning(f"action_node hit MAX_ITERATIONS ({MAX_ITERATIONS})")

        # Only store the final AI response in state, not ToolMessages
        state["messages"] = [HumanMessage(content=user_text), messages[-1]]

        # Keyword fallback if no tools were called at all
        if not cards:
            wo_type = None
            text = user_text.lower()
            if any(kw in text for kw in ["报修", "维修", "坏了", "故障", "堵了", "漏水", "不制冷", "不工作", "工单"]):
                wo_type = "repair"
            elif any(kw in text for kw in ["送物", "送东西", "送过来", "拿瓶", "拿个"]):
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
                            await _broadcast_work_order(wo_args, str(result))
                            break

    except Exception as e:
        logger.error(f"action_node failed: {e}", exc_info=True)
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content="抱歉，操作执行失败，请联系前台处理。"))
    state["business_cards"] = cards
    return state


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("chat_response", chat_node)
    workflow.add_node("knowledge_response", knowledge_node)
    workflow.add_node("action_response", action_node)

    # 条件路由：语义分类
    async def route_by_intent(state: AgentState):
        last_msg = state["messages"][-1] if state["messages"] else None
        user_text = last_msg.content if last_msg else ""
        try:
            intent = await classify_intent(user_text)
        except Exception as e:
            logger.error(f"classify_intent failed: {e}")
            intent = "chat"
        state["intent"] = intent
        print(f"[GRAPH-PRINT] route_by_intent: '{user_text[:30]}' → {intent}", flush=True)
        return intent

    workflow.add_conditional_edges(
        START,
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
