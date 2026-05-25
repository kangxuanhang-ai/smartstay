from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage
from langchain_deepseek import ChatDeepSeek

from app.core.config import settings
from app.ai.state import AgentState
from app.ai.tools import llm_classifier, classify_intent, build_tools
from app.ai.guard import execute_security_guard

llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.3,
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
    resp = await llm.ainvoke([SystemMessage(content="你是智宿云酒店的AI虚拟管家，友好、专业、简洁地回复住客。"), *state["messages"]])
    state["messages"].append(resp)
    state["business_cards"] = []
    return state


async def knowledge_node(state: AgentState):
    """知识库检索回复"""
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""

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
    state["business_cards"] = []
    return state


async def action_node(state: AgentState):
    """Tool Calling 执行节点"""
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""

    tools = build_tools()
    llm_with_tools = llm.bind_tools(tools)

    from langchain_core.messages import HumanMessage
    resp = await llm_with_tools.ainvoke([HumanMessage(content=user_text)])

    cards = []
    if resp.tool_calls:
        for call in resp.tool_calls:
            tool_name = call["name"]
            tool_args = call["args"]

            # 安全拦截
            guard_result = execute_security_guard(tool_name, state["role"], tool_args, user_text)
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
                    result = t.invoke(tool_args)
                    card_title = (
                        "🔧 空调调节中" if tool_name == "control_device_tool"
                        else "📦 物品配送工单已创建" if tool_name == "create_work_order_tool"
                        else "📚 知识库检索" if tool_name == "query_knowledge_tool"
                        else f"已执行：{tool_name}"
                    )
                    cards.append({"type": "success", "title": card_title, "detail": str(result)})
                    break

    state["messages"].append(resp)
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
