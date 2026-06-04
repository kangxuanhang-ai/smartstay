import asyncio
import logging

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_deepseek import ChatDeepSeek

from app.core.config import settings

logger = logging.getLogger(__name__)

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


HOTEL_LOCATION = "北京王府井"

_LOCATION_KEYWORDS = ["天气", "附近", "餐厅", "美食", "景点", "交通", "怎么去", "导航", "公交", "地铁", "路线", "距离", "多远", "多近", "怎么走"]


async def web_search_node(state):
    from app.ai.graph import _get_guest_name

    last_msg = state["messages"][-1] if state["messages"] else None
    user_text = last_msg.content if last_msg else ""

    # 位置相关查询自动拼接酒店位置
    search_query = user_text
    if any(kw in user_text for kw in _LOCATION_KEYWORDS):
        search_query = f"{HOTEL_LOCATION} {user_text}"

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
            f"## 搜索结果\n"
            f"{results_text}\n\n"
            f"## 回答规则\n"
            f"- 只基于以上搜索结果回答，不要编造信息\n"
            f"- 如果搜索结果中没有相关信息，诚实说没有\n"
            f"- 回答简洁友好，适合住客阅读\n"
            f"- 不要提及“搜索结果”等字眼\n"
            f"- 控制在 150 字以内，除非住客要求详细说明\n"
            f"- 如果是天气/交通等实时信息，提醒住客信息可能有延迟"
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
