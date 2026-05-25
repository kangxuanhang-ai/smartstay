from datetime import datetime
from langchain_deepseek import ChatDeepSeek
from app.core.config import settings
from app.core.database import async_session
from app.models.ai_log import AIPricingLog
from app.models.room import Room

llm = ChatDeepSeek(
    model="deepseek-chat",
    api_key=settings.DEEPSEEK_API_KEY,
    temperature=0.3,
)


async def trigger_pricing_agent(room_type: str, trigger_reason: str) -> dict:
    """AI 定价 Agent：分析市场数据 → 计算建议价格 → INSERT ai_pricing_logs(pending) → 返回结果"""
    async with async_session() as db:
        from sqlmodel import select
        result = await db.execute(select(Room).where(Room.room_type == room_type).limit(1))
        room = result.scalar_one_or_none()
        if not room:
            return {"error": f"房型 {room_type} 不存在"}

        base_price_yuan = room.base_price / 100
        current_price_yuan = room.current_price / 100

        prompt = (
            f"你是酒店收益管理AI专家。当前房型为 {room_type}，基础定价 ¥{base_price_yuan:.0f}，当前售价 ¥{current_price_yuan:.0f}。\n"
            f"触发调价原因：{trigger_reason}\n\n"
            f"请分析市场状况，输出建议新价格（精确到元）及调价理由。\n"
            f"输出格式（仅JSON）：{{\"suggested_price_yuan\": 数字, \"analysis\": \"理由\"}}\n"
            f"注意：涨幅不得超过基础价的 50%（即不超过 ¥{base_price_yuan * 1.5:.0f}）"
        )
        resp = await llm.ainvoke(prompt)
        text = resp.content.strip()

        import json
        try:
            parsed = json.loads(text.replace("```json", "").replace("```", "").strip())
            suggested_yuan = float(parsed.get("suggested_price_yuan", current_price_yuan))
            analysis = parsed.get("analysis", trigger_reason)
        except (json.JSONDecodeError, ValueError):
            suggested_yuan = current_price_yuan * 1.2
            analysis = trigger_reason

        suggested_cents = int(suggested_yuan * 100)
        max_cents = int(base_price_yuan * 1.5 * 100)
        if suggested_cents > max_cents:
            suggested_cents = max_cents

        log = AIPricingLog(
            room_type=room_type,
            trigger_reason=trigger_reason,
            original_price=room.current_price,
            suggested_price=suggested_cents,
            status="pending",
            suggested_by="AI · 定价Agent",
            created_at=datetime.utcnow(),
        )
        db.add(log)
        await db.commit()
        await db.refresh(log)

        return {
            "log_id": str(log.id),
            "room_type": room_type,
            "original_price": room.current_price,
            "suggested_price": suggested_cents,
            "analysis": analysis,
        }
