import uuid
import logging
from datetime import datetime
from typing import Any
from langchain_core.tools import tool
from langchain_deepseek import ChatDeepSeek
from sqlmodel import select, func, update

from app.core.config import settings
from app.core.database import async_session
from app.core.utils import cst_now
from app.models.work_order import WorkOrder
from app.models.room import Room

logger = logging.getLogger(__name__)

llm_classifier = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0,
)


_STRONG_ACTION_KEYWORDS = [
    "报修", "工单", "维修", "送物", "配送", "打扫", "清洁",
    "坏了", "故障", "不工作", "不制冷", "不热", "漏水", "堵了", "堵了",
    "开灯", "关灯", "开窗帘", "关窗帘", "调温度", "调空调",
]

_WEAK_ACTION_KEYWORDS = ["帮我", "请帮", "麻烦", "需要"]

_WEB_SEARCH_KEYWORDS = [
    "天气", "附近", "推荐", "怎么去", "导航", "航班", "地铁",
    "新闻", "景点", "美食", "餐厅", "好吃", "好玩", "旅游",
    "高铁", "火车", "飞机", "公交", "路线",
    "今天", "明天", "昨天", "几点", "日期", "时间", "现在",
    "星期", "周几", "几号", "几月",
    "距离", "多远", "多近", "多少米", "公里", "步行",
]


def _keyword_fallback(user_input: str) -> str | None:
    '""Keyword fallback: strong keywords match directly, weak keywords need an action word.""'
    text = user_input.lower()
    if any(kw in text for kw in _STRONG_ACTION_KEYWORDS):
        return "action"
    if any(kw in text for kw in _WEB_SEARCH_KEYWORDS):
        return "web_search"
    if any(kw in text for kw in _WEAK_ACTION_KEYWORDS):
        if any(op in text for op in ["开", "关", "调", "修", "送", "打扫", "清洁"]):
            return "action"
    return None


async def classify_intent(user_input: str) -> str:
    '""语义分析：让 LLM 判断用户意图，返回 chat / knowledge / action / web_search""'
    # 关键词兜底优先
    fallback = _keyword_fallback(user_input)
    if fallback:
        print(f"[CLASSIFY-PRINT] 关键词兜底命中: '{user_input[:30]}' → {fallback}", flush=True)
        return fallback

    prompt = (
        "你是酒店AI管家的意图分类器。分析住客输入，严格输出以下四者之一：\n\n"
        "- chat: 普通闲聊、打招呼、感谢、抱怨（不涉及具体操作请求）\n"
        "- knowledge: 询问酒店信息、政策、规则、设施等，包括：\n"
        "  · 设施位置、营业时间、价格\n"
        "  · 退房/入住/延迟退房等政策\n"
        "  · 酒店服务内容和流程\n"
        "  · 任何「能不能/可不可以/怎么办/是什么」类问题\n"
        "- action: 需要立即执行的具体操作：\n"
        "  · 控制房间设备（开/关灯、窗帘、调空调温度、切换空调模式）\n"
        "  · 创建工单/报修/送物\n"
        "- web_search: 需要联网查询的外部信息：\n"
        "  · 天气、新闻、赛事\n"
        "  · 附近餐厅/景点/交通推荐\n"
        "  · 实时信息（航班、地铁运营时间）\n"
        "  · 酒店知识库里没有的外部知识\n\n"
        "⚠️ 重要：询问政策/规则/流程 → knowledge，不是 action！\n"
        "⚠️ 重要：天气/交通/餐厅/景点 → web_search，不是 chat！\n"
        "⚠️ 重要：询问今天/明天的日期、星期几、几月几号、当前时间 → web_search，不是 chat！\n\n"
        "示例：\n"
        "- '你好' → chat\n"
        "- '谢谢' → chat\n"
        "- '空调好像坏了' → action\n"
        "- '帮我开灯' → action\n"
        "- '健身房几点开门？' → knowledge\n"
        "- '延迟退房怎么办？' → knowledge\n"
        "- '房间wifi密码是什么' → knowledge\n"
        "- '今天北京天气怎么样' → web_search\n"
        "- '附近有什么好吃的餐厅' → web_search\n"
        "- '从酒店到机场怎么走' → web_search\n"
        "- '明天有CBA比赛吗' → web_search\n"
        "- '今天是周几' → web_search\n"
        "- '现在几点了' → web_search\n"
        "- '今天几号' → web_search\n\n"
        f"住客输入：{user_input}\n\n"
        "只输出一个词（chat / knowledge / action / web_search），不要任何解释。"
    )
    resp = await llm_classifier.ainvoke(prompt)
    result = resp.content.strip().lower()
    print(f"[CLASSIFY-PRINT] LLM原始回复: '{resp.content}' → 处理后: '{result}'", flush=True)
    if result in ("chat", "knowledge", "action", "web_search"):
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

        # 通知住客 Flutter 刷新设备状态
        try:
            from app.ws.manager import manager as ws_manager
            await ws_manager.send_to_room(room_id, {
                "event": "device_state_change",
                "data": {"device": device, "value": value, "states": states},
            })
        except Exception:
            pass

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
                created_at=cst_now(),
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
    return "\n——\n".join(docs)


# ── Tool 4: 修改房价（仅 manager）──
@tool
def modify_room_price_tool(room_type: str, new_price_yuan: float) -> str:
    """
    修改指定房型的当前价格。仅店长(manager)可调用。
    room_type: big_bed / twin / suite
    new_price_yuan: 新价格（元），涨幅不超过 base_price 的 150%
    """
    return f"调价请求已记录：{room_type} → ¥{new_price_yuan}（待审批）"


# ── Tool 5: 保存住客偏好 ──
@tool
async def save_preference_tool(key: str, value: str, guest_id: str = "") -> str:
    """
    保存住客的环境偏好设置。只在住客明确表达长期偏好时调用。
    key: ac_temp / curtain / bedside_light / bedroom_light / living_light / ac_mode
    value: 对应值，如 "24", "80", "true", "cool"
    guest_id: 由系统自动注入，勿手动填写
    """
    if not guest_id:
        return "错误：缺少 guest_id，无法保存偏好"
    try:
        from app.models.preference import GuestPreference
        async with async_session() as db:
            result = await db.execute(
                select(GuestPreference).where(
                    GuestPreference.guest_id == uuid.UUID(guest_id),
                    GuestPreference.key == key,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.value = value
                existing.updated_at = cst_now()
            else:
                pref = GuestPreference(
                    guest_id=uuid.UUID(guest_id),
                    key=key,
                    value=value,
                    updated_at=cst_now(),
                )
                db.add(pref)
            await db.commit()
        return f"偏好已保存：{key} = {value}"
    except Exception as e:
        logger.error(f"save_preference_tool failed: {e}")
        return f"错误：保存偏好失败 - {e}"


# ── 工具集合 ──
def build_tools():
    return [
        control_device_tool,
        create_work_order_tool,
        query_knowledge_tool,
        modify_room_price_tool,
        save_preference_tool,
    ]
