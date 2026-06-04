"""投诉检测模块：关键词触发 + LLM 二次确认"""

import json
import logging
from langchain_deepseek import ChatDeepSeek
from app.core.config import settings

logger = logging.getLogger(__name__)

COMPLAINT_KEYWORDS = [
    "投诉", "不满", "差评", "太差", "垃圾", "恶心", "退款", "换房",
    "受不了", "忍不了", "态度差", "服务差", "不干净", "有虫", "漏水",
    "没热水", "太吵", "隔音差", "骗人", "坑人", "报警", "消协", "12315",
    "举报", "曝光", "差劲", "恶劣", "愤怒", "气死",
]

_llm_sentiment = None


def _get_sentiment_llm():
    global _llm_sentiment
    if _llm_sentiment is None:
        _llm_sentiment = ChatDeepSeek(
            model="deepseek-chat",
            api_key=settings.DEEPSEEK_API_KEY,
            temperature=0,
        )
    return _llm_sentiment


async def detect_complaint(user_input: str) -> dict:
    """检测是否为投诉/不满。

    关键词只作为"疑似"触发器，必须经 LLM 二次确认才判定为投诉。
    返回: {"is_complaint": bool, "severity": "low"|"medium"|"high", "summary": str}
    """
    # 关键词匹配
    suspicious = any(kw in user_input for kw in COMPLAINT_KEYWORDS)

    # LLM 二次确认（无论是否命中关键词都走这一步）
    try:
        llm = _get_sentiment_llm()
        prompt = (
            "你是一个酒店 AI 情感分析器。判断以下住客消息是否表达真实的不满、投诉或强烈负面情绪。\n"
            "注意区分：\n"
            '- 报修/求助（如"空调不太好用"）→ 不是投诉，是正常服务请求\n'
            '- 闲聊评价（如"房间有点小"）→ 不是投诉，是闲聊\n'
            '- 真正的投诉/不满（如"服务太差了"、"我要投诉"、"受不了了"）→ 是投诉\n\n'
            f"suspicious（关键词匹配）: {suspicious}\n"
            f"消息：{user_input}\n\n"
            '只输出 JSON：{"is_complaint": true/false, "severity": "low/medium/high", "summary": "一句话总结"}'
        )
        resp = await llm.ainvoke(prompt)
        text = resp.content.strip()
        # 清理 markdown 代码块
        text = text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(text)
        return {
            "is_complaint": bool(parsed.get("is_complaint", False)),
            "severity": parsed.get("severity", "low"),
            "summary": parsed.get("summary", ""),
        }
    except Exception as e:
        logger.error(f"detect_complaint LLM failed: {e}")
        # LLM 失败时，如果关键词命中则保守判定为投诉
        if suspicious:
            return {"is_complaint": True, "severity": "medium", "summary": user_input[:50]}
        return {"is_complaint": False, "severity": "low", "summary": ""}