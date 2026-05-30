import uuid
import logging
from datetime import datetime, timezone
from typing import Any
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from sqlmodel import select, func, update

from app.core.config import settings
from app.core.database import async_session
from app.models.work_order import WorkOrder
from app.models.room import Room

logger = logging.getLogger(__name__)

llm_classifier = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0,
)


_ACTION_KEYWORDS = [
    "报修", "工单", "维修", "送物", "配送", "打扫", "清洁",
    "坏了", "故障", "不工作", "不制冷", "不热", "漏水", "堵塞", "堵了",
    "开灯", "关灯", "开窗帘", "关窗帘", "调温度", "调空调",
    "帮我", "请帮", "麻烦", "需要",
]


def _keyword_fallback(user_input: str) -> str | None:
    """关键词兜底：LLM 分类器不稳定时，用关键词强制判定 action"""
    text = user_input.lower()
    if any(kw in text for kw in _ACTION_KEYWORDS):
        return "action"
    return None


async def classify_intent(user_input: str) -> str:
    """语义分析：让 LLM 判断用户意图，返回 chat / knowledge / action"""
    # 关键词兜底优先
    fallback = _keyword_fallback(user_input)
    if fallback:
        print(f"[CLASSIFY-PRINT] 关键词兜底命中: '{user_input[:30]}' → {fallback}", flush=True)
        return fallback

    prompt = (
        "你是酒店AI管家的意图分类器。分析住客输入，严格输出以下三者之一：\n\n"
        "- chat: 普通闲聊、打招呼、感谢、抱怨（不涉及具体操作请求）\n"
        "- knowledge: 纯粹询问酒店信息（设施位置、营业时间、价格、政策等），不需要执行任何操作\n"
        "- action: 所有需要酒店执行操作的请求，包括但不限于：\n"
        "  · 控制房间设备（开/关灯、窗帘、调空调温度、切换空调模式）\n"
        "  · 创建工单/报修/送物（如：马桶坏了、空调不制冷、送瓶水、请打扫房间、帮我报修、创建维修工单）\n"
        "  · 任何包含报修、工单、送、修、坏、不工作、不制冷、漏水等维修/服务关键词的请求\n\n"
        "关键判断：如果住客希望你帮他做某件事（而不是仅仅问个问题），就是 action。\n\n"
        "示例：\n"
        "- '空调坏了' → action\n"
        "- '帮我开灯' → action\n"
        "- '请送一瓶矿泉水' → action\n"
        "- '健身房几点开门？' → knowledge\n"
        "- '你好' → chat\n\n"
        f"住客输入：{user_input}\n\n"
        "只输出一个词（chat / knowledge / action），不要任何解释："
    )
    resp = await llm_classifier.ainvoke(prompt)
    result = resp.content.strip().lower()
    print(f"[CLASSIFY-PRINT] LLM分类结果: '{user_input[:30]}' → {result}", flush=True)
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
    wo_type = type  # 保存参数，避免覆盖 builtin type
    print(f"[TOOL-PRINT] create_work_order_tool 被调用: type={wo_type}, room_id={room_id}, content={content}", flush=True)
    if not room_id:
        print("[TOOL-PRINT] room_id 为空，无法创建工单", flush=True)
        return "错误：缺少 room_id，无法创建工单"
    try:
        async with async_session() as db:
            # 熔断：待处理工单总数上限
            result = await db.execute(
                select(func.count()).where(
                    WorkOrder.room_id == uuid.UUID(room_id),
                    WorkOrder.status.in_(["submitted", "accepted", "processing"]),
                )
            )
            pending_count = result.scalar() or 0
            if pending_count >= 20:
                print(f"[TOOL-PRINT] 熔断拦截: pending_count={pending_count}", flush=True)
                return f"安全熔断：该房间未结工单已达 {pending_count} 个上限，请稍后再试"

            wo = WorkOrder(
                room_id=uuid.UUID(room_id),
                type=wo_type,
                content=content,
                status="submitted",
                ai_generated=True,
                created_at=datetime.utcnow(),
            )
            db.add(wo)
            await db.commit()
            await db.refresh(wo)
            print(f"[TOOL-PRINT] 工单写入成功 id={wo.id} room_id={room_id} type={wo_type}", flush=True)
            return f"工单已创建：{wo_type} — {content} [order_id={wo.id}]"
    except Exception as e:
        print(f"[TOOL-PRINT] 创建工单异常: {e.__class__.__name__}: {e}", flush=True)
        return f"错误：创建工单失败 - {e}"


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
