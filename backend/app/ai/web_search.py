import asyncio
import logging
import re

import httpx
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_deepseek import ChatDeepSeek

from app.core.config import settings

logger = logging.getLogger(__name__)

_WEATHER_KEYWORDS = ["天气", "气温", "温度", "下雨", "下雪", "刮风", "晴天", "阴天", "多云"]

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatDeepSeek(
            model="deepseek-chat",
            api_key=settings.DEEPSEEK_API_KEY,
            temperature=0.3,
        )
    return _llm


async def search_web(query: str, num_results: int = 3) -> list:
    if not settings.SERPAPI_KEY:
        logger.warning("SERPAPI_KEY not configured, skipping web search")
        return []

    try:
        from serpapi import GoogleSearch

        params = {
            "q": query,
            "api_key": settings.SERPAPI_KEY,
            "engine": "google",
            "hl": "zh-cn",
            "gl": "cn",
            "num": num_results,
        }
        search = GoogleSearch(params)
        results = await asyncio.to_thread(search.get_dict)

        organic = results.get("organic_results", [])
        formatted = []
        for item in organic[:num_results]:
            formatted.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", "")[:100],
                "link": item.get("link", ""),
            })

        answer_box = results.get("answer_box")
        if answer_box:
            answer = answer_box.get("answer") or answer_box.get("snippet") or ""
            if answer:
                formatted.insert(0, {
                    "title": answer_box.get("title", "答案"),
                    "snippet": str(answer)[:100],
                    "link": "",
                })

        return formatted
    except Exception as e:
        logger.error(f"SerpAPI search failed: {type(e).__name__}: {e}")
        return []


def _is_weather_query(text: str) -> bool:
    return any(kw in text for kw in _WEATHER_KEYWORDS)


def _extract_city(text: str) -> str:
    """从用户消息中提取城市名，默认北京"""
    # 尝试匹配 "XX天气" 模式
    m = re.search(r"([一-鿿]{2,4})(?:的)?天气", text)
    if m:
        return m.group(1)
    # 尝试匹配 "XX市"
    m = re.search(r"([一-鿿]{2,4})市", text)
    if m:
        return m.group(1)
    return "北京"


async def _search_weather(query: str) -> str:
    """通过 wttr.in 获取天气（免费，无需 API key）"""
    city = _extract_city(query)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://wttr.in/{city}",
                params={"format": "j1", "lang": "zh"},
                headers={
                    "Accept-Language": "zh-CN",
                    "User-Agent": "SmartStay/1.0 (hotel-ai-assistant)",
                },
            )
            if resp.status_code != 200:
                logger.warning(f"wttr.in returned {resp.status_code}")
                return ""
            data = resp.json()

            current = data.get("current_condition", [{}])[0]
            temp_c = current.get("temp_C", "?")
            feels_like = current.get("FeelsLikeC", "?")
            desc = current.get("lang_zh", [{}])[0].get("value", "")
            if not desc:
                desc = current.get("weatherDesc", [{}])[0].get("value", "")
            humidity = current.get("humidity", "?")
            wind_speed = current.get("windspeedKmph", "?")

            # 获取今天预报
            today = data.get("weather", [{}])[0]
            max_temp = today.get("maxtempC", "?")
            min_temp = today.get("mintempC", "?")

            result = (
                f"{city}今天天气：{desc}，"
                f"当前温度 {temp_c}°C（体感 {feels_like}°C），"
                f"最高 {max_temp}°C / 最低 {min_temp}°C，"
                f"湿度 {humidity}%，风速 {wind_speed}km/h"
            )
            return result
    except Exception as e:
        logger.error(f"wttr.in weather query failed: {e}")
        return ""


async def _get_hotel_location() -> str:
    """从数据库读取酒店地址，读不到则用默认值"""
    try:
        from app.core.database import async_session
        from app.models.hotel import HotelInfo
        from sqlmodel import select
        async with async_session() as db:
            result = await db.execute(select(HotelInfo.address).limit(1))
            address = result.scalar_one_or_none()
            if address:
                return address
    except Exception:
        pass
    return "北京市朝阳区建国路88号SOHO现代城"

_LOCATION_KEYWORDS = ["天气", "附近", "位置", "旁边", "餐厅", "美食", "景点", "交通", "怎么去", "导航", "公交", "地铁", "路线", "距离", "多远", "多近", "怎么走", "好玩", "推荐", "周边"]


_PRONOUNS = ["这些", "那个", "这里", "那里", "它", "它们", "这个", "那个"]


async def web_search_node(state):
    from app.ai.graph import _get_guest_name
    from app.core.utils import cst_now

    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""
    current_time = cst_now().strftime("%Y-%m-%d %H:%M")

    # 天气查询走 wttr.in（不依赖 SerpAPI）
    if _is_weather_query(user_text):
        weather_info = await _search_weather(user_text)
        if weather_info:
            guest_name = await _get_guest_name(state.get("user_id", ""))
            system_msg = SystemMessage(content=(
                f"你是酒店智能管家小智，正在为住客{guest_name}提供天气查询服务。\n\n"
                f"## 天气数据\n{weather_info}\n\n"
                f"## 回答规则\n"
                f"- 基于以上天气数据回答，简洁友好\n"
                f"- 适当给出穿衣或出行建议\n"
                f"- 控制在 100 字以内"
            ))
            resp = await _get_llm().ainvoke([system_msg, HumanMessage(content=user_text)])
            return {
                "messages": [resp],
                "business_cards": [],
            }
        # wttr.in 失败则继续走 SerpAPI 兜底

    # 追问检测：如果用户消息含代词，用上一轮 AI 回复补充上下文生成搜索词
    search_query = user_text
    if any(p in user_text for p in _PRONOUNS) and len(state["messages"]) >= 2:
        prev_ai = None
        for m in reversed(state["messages"][:-1]):
            if hasattr(m, "type") and m.type == "ai":
                prev_ai = m.content
                break
            elif hasattr(m, "content") and m.type != "human":
                prev_ai = m.content
                break
        if prev_ai:
            # 提取上一轮回复中的关键名词短语（取前80字作为上下文）
            context = prev_ai[:80]
            search_query = f"{context} {user_text}"

    # 位置相关查询自动拼接酒店位置
    if any(kw in user_text for kw in _LOCATION_KEYWORDS):
        hotel_location = await _get_hotel_location()
        search_query = f"{hotel_location} {search_query}"

    try:
        search_results = await search_web(search_query)

        if not search_results:
            return {
                "messages": [AIMessage(content="抱歉，联网搜索未找到相关信息，请换个问题试试。")],
                "business_cards": [],
            }

        guest_name = await _get_guest_name(state.get("user_id", ""))

        results_text = "\n".join(
            f"[{i+1}] {r['title']}\n    {r['snippet']}"
            for i, r in enumerate(search_results)
            if r.get("snippet")
        )

        system_msg = SystemMessage(content=(
            f"你是酒店智能管家小智，正在为住客{guest_name}提供联网搜索服务。\n\n"
            f"## 当前时间\n"
            f"{current_time}\n\n"
            f"## 搜索结果\n"
            f"{results_text}\n\n"
            f"## 回答规则\n"
            f"- 只基于以上搜索结果回答，不要编造信息\n"
            f"- 如果搜索结果中没有相关信息，诚实说没有\n"
            f"- 回答简洁友好，适合住客阅读\n"
            f'- 不要提及"搜索结果"等字眼\n'
            f"- 控制在 150 字以内，除非住客要求详细说明\n"
            f"- 如果是天气/交通等实时信息，提醒住客信息可能有延迟\n"
            f"- 今天的日期是 {current_time}，回答中涉及日期时使用真实日期"
        ))

        resp = await _get_llm().ainvoke([system_msg, HumanMessage(content=user_text)])
        return {
            "messages": [resp],
            "business_cards": [],
        }

    except Exception as e:
        logger.error(f"web_search_node failed: {e}", exc_info=True)
        return {
            "messages": [AIMessage(content="抱歉，联网搜索暂时不可用，请稍后再试。")],
            "business_cards": [],
        }
