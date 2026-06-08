from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage, AIMessage
from langchain_deepseek import ChatDeepSeek
import logging
import re

from app.core.config import settings
from app.core.utils import cst_now
from app.ai.state import AgentState
from app.ai.tools import classify_intent, build_tools
from app.ai.guard import execute_security_guard
from app.ai.complaint import detect_complaint
from app.ai.web_search import web_search_node

logger = logging.getLogger(__name__)

llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.3,
    streaming=True,
)


async def _get_guest_name(user_id: str) -> str:
    '""查询住客姓名""'
    try:
        import uuid
        from app.core.database import async_session
        from app.models.guest import Guest
        from sqlmodel import select
        async with async_session() as db:
            result = await db.execute(select(Guest.name).where(Guest.id == uuid.UUID(user_id)))
            return result.scalar_one_or_none() or "住客"
    except Exception:
        return "住客"


async def chat_node(state: AgentState):
    '""闲聊回复""'
    try:
        from app.core.utils import cst_now
        recent = state["messages"][-10:]
        user_count = sum(1 for m in recent if hasattr(m, "type") and m.type == "human")

        # 获取住客信息
        guest_name = await _get_guest_name(state.get("user_id", ""))
        room_id = state.get("room_id", "")
        current_time = cst_now().strftime("%Y-%m-%d %H:%M")

        # 通过 room_id 查询实际房间号
        room_number = "未知"
        if room_id:
            try:
                from app.models.room import Room
                from app.core.database import async_session
                from sqlmodel import select as sql_select
                import uuid as _uuid
                async with async_session() as db:
                    room_res = await db.execute(sql_select(Room.room_number).where(Room.id == _uuid.UUID(room_id)))
                    room_number = room_res.scalar_one_or_none() or "未知"
            except Exception:
                room_number = "未知"

        # 获取酒店地址
        hotel_address = "北京市朝阳区建国路88号SOHO现代城"
        try:
            from app.models.hotel import HotelInfo
            from app.core.database import async_session as _db_session
            from sqlmodel import select as _sel
            async with _db_session() as _db:
                _addr_res = await _db.execute(_sel(HotelInfo.address).limit(1))
                _addr = _addr_res.scalar_one_or_none()
                if _addr:
                    hotel_address = _addr
        except Exception:
            pass

        # 偏好信息
        preferences = state.get("preferences") or {}
        pref_text = ""
        if preferences:
            pref_items = []
            if "ac_temp" in preferences:
                pref_items.append(f"空调{preferences['ac_temp']}°C")
            if "curtain" in preferences:
                pref_items.append(f"窗帘{preferences['curtain']}%")
            if "bedside_light" in preferences:
                pref_items.append(f"床头灯{'开' if preferences['bedside_light'] == 'true' else '关'}")
            if "bedroom_light" in preferences:
                pref_items.append(f"卧室灯{'开' if preferences['bedroom_light'] == 'true' else '关'}")
            if "living_light" in preferences:
                pref_items.append(f"客厅灯{'开' if preferences['living_light'] == 'true' else '关'}")
            if pref_items:
                pref_text = f"\n住客偏好设置：{'、'.join(pref_items)}"

        # 摘要信息
        summary = state.get("conversation_summary") or ""
        summary_text = f"\n\n【对话摘要】\n{summary}" if summary else ""

        system_msg = SystemMessage(content=(
            f"你是「小智」，智宿云酒店的 AI 虚拟管家。\n\n"
            f"## 身份\n"
            f"- 你住在手机 App 里，为住客提供 24 小时智能服务\n"
            f"- 你友好、专业、温暖，像一个贴心的酒店管家\n\n"
            f"## 当前上下文\n"
            f"- 时间：{current_time}\n"
            f"- 住客：{guest_name}\n"
            f"- 房间号：{room_number}\n"
            f"- 酒店地址：{hotel_address}\n"
            f"- 对话轮次：住客已发送 {user_count} 条消息"
            f"{pref_text}{summary_text}\n\n"
            f"## 回复规范\n"
            f"- 简短操作回复（控制设备、确认操作）用纯文本，50 字以内\n"
            f"- 信息量较大的回复（设施介绍、政策说明）允许使用 **加粗** 和 - 列表，但不要用标题和代码块\n"
            f"- 不要重复住客的原话\n"
            f"- 如果住客问的问题你不确定，诚实说不确定并建议联系前台\n\n"
            f"## 示例\n"
            f"住客：你好\n"
            f"小智：您好！有什么可以帮您的吗？\n\n"
            f"住客：空调调到 25 度\n"
            f"小智：好的，已为您调整。\n\n"
            f"住客：游泳池几点关门？\n"
            f"小智：游泳池开放时间是 **06:00-23:00**，恒温 26°C，免费提供浴巾和更衣柜。"
        ))
        resp = await llm.ainvoke([system_msg, *recent])
        state["messages"].append(resp)
    except Exception:
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content="抱歉，系统暂时无法回复，请稍后再试或联系前台。"))
    state["business_cards"] = []
    return state


async def knowledge_node(state: AgentState):
    '""知识库检索回复""'
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""

    try:
        from app.ai.rag import query_vector_store
        docs = await query_vector_store(user_text)
        context = "\n".join(docs) if docs else "知识库无匹配信息"

        guest_name = await _get_guest_name(state.get("user_id", ""))
        room_id = state.get("room_id", "")

        # 通过 room_id 查询实际房间号
        room_number = "未知"
        if room_id:
            try:
                from app.models.room import Room
                from app.core.database import async_session
                from sqlmodel import select as sql_select
                import uuid as _uuid
                async with async_session() as db:
                    room_res = await db.execute(sql_select(Room.room_number).where(Room.id == _uuid.UUID(room_id)))
                    room_number = room_res.scalar_one_or_none() or "未知"
            except Exception:
                room_number = "未知"

        recent = state["messages"][-5:]
        recent_text = "\n".join(f"{m.type}: {m.content}" for m in recent if hasattr(m, "content") and m.content)
        system_prompt = (
            f"你是「小智」，智宿云酒店的 AI 虚拟管家。\n"
            f"当前住客：{guest_name}，房间号：{room_number}\n\n"
            f"请严格依据以下酒店知识库信息回答住客问题。\n"
            f"- 如果知识库没有相关信息，诚实告知住客并建议联系前台（电话或 App 内消息）\n"
            f"- 绝对不要编造知识库中没有的信息\n"
            f"- 回答简洁专业，信息量大时使用加粗和列表\n\n"
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
        return "📋 工单已创建"
    if tool_name == "query_knowledge_tool":
        return "📖 知识库检索"
    return f"✅ {tool_name}已执行"


async def _broadcast_work_order(tool_args: dict, result: str):
    '""Broadcast work order creation via WebSocket.""'
    if "工单已创建" not in str(result):
        return
    try:
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
    '""Execute a single tool call, return card and optional tool message.""'
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

    # Inject guest_id for preference tool
    if tool_name == "save_preference_tool" and state.get("user_id"):
        tool_args["guest_id"] = state["user_id"]

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


def _is_all_lights_command(text: str) -> bool:
    '""检测用户是否在要求操作所有灯光""'
    t = text.lower()
    return bool(re.search(r'(所有|全部|所有|全部|统统|都).*(灯|灯光|灯关|灯开)', t)
                or re.search(r'(灯|灯光|灯关|灯开).*(所有|全部|所有|全部|统统|都)', t)
                or t in ("开灯", "关灯", "打开灯", "关闭灯", "把灯打开", "把灯关了", "把灯打开", "把灯关掉"))


def _want_lights_on(text: str) -> bool:
    '""判断用户想开灯还是关灯""'
    t = text.lower()
    if re.search(r'(打开|开|开启|亮|点亮|亮起)', t):
        return True
    if re.search(r'(关闭|关|关掉|熄灭|灭|暗)', t):
        return False
    return True  # 默认开


async def action_node(state: AgentState):
    '""Tool Calling with multi-step agent loop.""'
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""
    # 去掉用户输入中的房间号，防止 LLM 控制别的房间
    clean_text = re.sub(r'\d{3,4}号?房?间?|room\s*\d+', '', user_text).strip()
    if not clean_text:
        clean_text = user_text
    logger.info(f"action_node entered, user_text={clean_text[:50]}")

    # 价格相关请求直接拦截（不依赖 LLM tool_call）
    _price_keywords = ["房价", "价格", "改价", "调价", "打折", "减免", "免单"]
    if any(kw in clean_text for kw in _price_keywords):
        from app.ai.guard import execute_security_guard, _log_violation
        guard_result = await execute_security_guard(
            "modify_room_price_tool", state["role"], {"user_text": clean_text},
            clean_text, user_id=state.get("user_id", ""),
        )
        if not guard_result["ok"]:
            state["messages"].append(AIMessage(content=guard_result["error"]))
            state["business_cards"] = [{"type": "error", "title": "⚠️ 操作被拦截", "detail": guard_result["error"]}]
            return state

    # 偏好信息
    preferences = state.get("preferences") or {}
    pref_text = ""
    if preferences:
        pref_items = []
        if "ac_temp" in preferences:
            pref_items.append(f"空调{preferences['ac_temp']}°C")
        if "curtain" in preferences:
            pref_items.append(f"窗帘{preferences['curtain']}%")
        pref_items_str = "、".join(pref_items) if pref_items else "无"
        pref_text = f"\n住客偏好：{pref_items_str}"

    cards = []
    try:
        tools = build_tools()
        llm_with_tools = llm.bind_tools(tools)

        system_msg = SystemMessage(content=(
            f"你是「小智」，智宿云酒店的 AI 虚拟管家。当前住客需要你执行具体操作。{pref_text}\n\n"
            f"## 可用工具\n"
            f"- control_device: 控制灯光（living_light/bedroom_light/bedside_light，bool）、窗帘（curtain，0-100）、空调温度（ac_temp，16-30）、空调模式（ac_mode，cool/heat）\n"
            f"- create_work_order: 创建送物(delivery)或报修(repair)工单\n"
            f"- query_knowledge: 检索酒店知识库\n"
            f"- save_preference: 保存住客长期偏好设置\n\n"
            f"## 核心约束\n"
            f"- room_id 由系统自动注入，不要在工具调用中指定 room_id\n"
            f"- 窗帘必须用 int（0=全关，100=全开），不能用 bool\n\n"
            f"### ⚠️ 批量操作规则（必须严格遵守）\n"
            f"- 住客说「所有灯光」「全部灯」「所有灯」「开灯/关灯」→ 必须同时调用 3 个工具：control_device(living_light, ...) + control_device(bedroom_light, ...) + control_device(bedside_light, ...)\n"
            f"- 住客说「所有窗帘」→ 调用 control_device(curtain, ...)\n"
            f"- 住客同时提出多个操作（如「空调调到25度并且把窗帘关闭」）→ 必须返回多个 tool_calls\n"
            f"- 一个 tool_call 只控制一个设备，不要试图用一个调用控制多个设备\n\n"
            f"## 偏好保存规则\n"
            f"- 只在住客明确表达长期偏好时才调用 save_preference（如「我喜欢25度」、「以后都调到25度」、「默认设为…」）\n"
            f"- 临时操作（如「调到20度」、「把灯关了」）不保存偏好，只执行设备控制\n\n"
            f"## 示例\n"
            f"住客：帮我开灯\n"
            f"→ control_device(living_light, true) + control_device(bedroom_light, true) + control_device(bedside_light, true)\n\n"
            f"住客：关掉所有灯\n"
            f"→ control_device(living_light, false) + control_device(bedroom_light, false) + control_device(bedside_light, false)\n\n"
            f"住客：把客厅灯打开\n"
            f"→ control_device(living_light, true)\n\n"
            f"住客：空调调到25度，窗帘关上\n"
            f"→ control_device(ac_temp, 25) + control_device(curtain, 0)\n\n"
            f"住客：我喜欢24度，以后默认这个温度\n"
            f"→ control_device(ac_temp, 24) + save_preference(ac_temp, 24)\n"
        ))

        messages = [system_msg, HumanMessage(content=clean_text)]

        for iteration in range(MAX_ITERATIONS):
            resp = await llm_with_tools.ainvoke(messages)

            if not resp.tool_calls:
                # LLM done calling tools
                if resp.content:
                    messages.append(resp)
                break

            # 顺序执行工具调用（设备控制不能并发，否则 device_states 会互相覆盖）
            results = []
            for call in resp.tool_calls:
                results.append(await _execute_single_tool(call, tools, state, user_text))

            # Feed results back to LLM (ToolMessages are local, not stored in state)
            messages.append(resp)  # assistant message with tool_calls
            for call, result in zip(resp.tool_calls, results):
                cards.append(result["card"])
                if result["tool_message"]:
                    call_id, detail = result["tool_message"]
                    messages.append(ToolMessage(content=detail, tool_call_id=call_id))
                    await _broadcast_work_order(call["args"], detail)

            # 回退：LLM 漏掉的灯光控制 → 自动补上
            if _is_all_lights_command(clean_text):
                called_devices = {
                    call["args"].get("device")
                    for call in resp.tool_calls
                    if call["name"] == "control_device_tool"
                }
                want_on = _want_lights_on(clean_text)
                for dev in ("living_light", "bedroom_light", "bedside_light"):
                    if dev not in called_devices:
                        fallback_args = {"device": dev, "value": want_on}
                        guard = await execute_security_guard(
                            "control_device_tool", state["role"], fallback_args,
                            user_text, user_id=state.get("user_id", ""),
                        )
                        if guard["ok"]:
                            for t in tools:
                                if t.name == "control_device_tool":
                                    result = await t.ainvoke(fallback_args)
                                    cards.append({
                                        "type": "success",
                                        "title": _get_card_title("control_device_tool", fallback_args),
                                        "detail": str(result),
                                    })
                                    break
        else:
            # MAX_ITERATIONS reached without LLM stopping
            logger.warning(f"action_node hit MAX_ITERATIONS ({MAX_ITERATIONS})")

        # 确保 LLM 生成最终文字回复
        from langchain_core.messages import AIMessage
        last_msg = messages[-1] if messages else None
        if not isinstance(last_msg, AIMessage) or not getattr(last_msg, 'content', ''):
            # 工具执行完但 LLM 没有生成文字回复，强制生成确认
            confirm_msg = HumanMessage(content="操作已执行，请用一句话简短确认。")
            messages.append(confirm_msg)
            resp = await llm.ainvoke(messages)
            messages.append(resp)

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
                            label = "🔧 报修工单已创建" if wo_type == "repair" else "📦 送物工单已创建"
                            cards.append({"type": "success", "title": label, "detail": str(result)})
                            await _broadcast_work_order(wo_args, str(result))
                            break

    except Exception as e:
        logger.error(f"action_node failed: {e}", exc_info=True)
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content="抱歉，操作执行失败，请联系前台处理。"))
    state["business_cards"] = cards
    return state


async def complaint_response(state: AgentState):
    '""投诉自动响应：安抚住客 + 通知前台 + 创建紧急工单""'
    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""
    room_id = state.get("room_id", "")
    guest_name = await _get_guest_name(state.get("user_id", ""))

    cards = []

    try:
        # 1. 生成安抚回复
        _default_reply = "非常抱歉给您带来不好的体验，已通知前台立即处理，请您稍等。"
        try:
            from app.ai.rag import _get_rewriter
            empathetic_llm = _get_rewriter()
            prompt = (
                f"住客{guest_name}在酒店App中表达了不满。请生成一段简短真诚的回复（50字以内）：\n"
                f"- 真诚道歉\n"
                f"- 告知已通知前台处理\n"
                f"- 承诺尽快解决\n"
                f"- 不要辩解或推卸责任\n\n"
                f"住客原话：{user_text}"
            )
            resp = await empathetic_llm.ainvoke(prompt)
            reply_text = resp.content.strip() if resp.content else ""
        except Exception:
            reply_text = ""

        if not reply_text:
            reply_text = _default_reply

        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content=reply_text))

        # 2. 创建紧急工单
        from app.core.database import async_session
        from app.models.work_order import WorkOrder
        import uuid as _uuid

        if room_id:
            async with async_session() as db:
                wo = WorkOrder(
                    room_id=_uuid.UUID(room_id),
                    type="complaint",
                    content=f"[投诉] {user_text[:200]}",
                    status="submitted",
                    ai_generated=True,
                    created_at=cst_now(),
                )
                db.add(wo)
                await db.commit()
                await db.refresh(wo)
                cards.append({
                    "type": "warning",
                    "title": "🚨 投诉已记录",
                    "detail": f"工单号：{wo.id}",
                })

        # 3. WebSocket 通知前台
        try:
            from app.ws.manager import manager as ws_manager
            from app.models.room import Room
            from app.core.database import async_session
            from sqlmodel import select as sql_select
            import uuid as _uuid

            room_number = "未知"
            if room_id:
                async with async_session() as db:
                    room_res = await db.execute(sql_select(Room.room_number).where(Room.id == _uuid.UUID(room_id)))
                    room_number = room_res.scalar_one_or_none() or "未知"

            await ws_manager.broadcast_biz({
                "event": "complaint.alert",
                "data": {
                    "room_number": room_number,
                    "room_id": room_id,
                    "guest_name": guest_name,
                    "message": user_text[:200],
                },
            })
        except Exception as e:
            logger.warning(f"Complaint WS broadcast failed: {e}")

        # 4. 记录安全日志
        try:
            from app.core.database import async_session
            from app.models.security_log import AISecurityLog
            async with async_session() as db:
                log = AISecurityLog(
                    user_id=_uuid.UUID(state.get("user_id", "")) if state.get("user_id") else None,
                    user_type="guest",
                    role=state.get("role", "guest"),
                    tool_name="complaint_response",
                    tool_params={"message": user_text[:200]},
                    violation_type="complaint",
                    user_input=user_text[:500],
                    intercepted_at=cst_now(),
                )
                db.add(log)
                await db.commit()
        except Exception:
            pass

    except Exception as e:
        logger.error(f"complaint_response failed: {e}", exc_info=True)
        from langchain_core.messages import AIMessage
        state["messages"].append(AIMessage(content="非常抱歉给您带来不便，已通知前台处理。"))

    state["business_cards"] = cards
    return state


def build_graph(web_search_enabled: bool = False):
    workflow = StateGraph(AgentState)

    workflow.add_node("chat_response", chat_node)
    workflow.add_node("knowledge_response", knowledge_node)
    workflow.add_node("action_response", action_node)
    workflow.add_node("web_search_response", web_search_node)

    # 条件路由：语义分类
    async def route_by_intent(state: AgentState):
        last_msg = state["messages"][-1] if state["messages"] else None
        user_text = last_msg.content if last_msg else ""

        # 先检测投诉（关键词 + LLM 二次确认）
        try:
            complaint_result = await detect_complaint(user_text)
            if complaint_result["is_complaint"]:
                state["intent"] = "complaint"
                print(f"[GRAPH-PRINT] complaint detected: '{user_text[:30]}' severity={complaint_result['severity']}", flush=True)
                return "complaint"
        except Exception as e:
            logger.error(f"detect_complaint failed: {e}")

        # 非投诉，走正常意图分类
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
            "complaint": "complaint_response",
            "web_search": "web_search_response" if web_search_enabled else "chat_response",
        },
    )

    workflow.add_node("complaint_response", complaint_response)
    workflow.add_edge("chat_response", END)
    workflow.add_edge("knowledge_response", END)
    workflow.add_edge("action_response", END)
    workflow.add_edge("web_search_response", END)
    workflow.add_edge("complaint_response", END)

    return workflow.compile(checkpointer=MemorySaver())