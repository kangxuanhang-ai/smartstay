import uuid
from datetime import datetime

from app.core.database import async_session
from app.core.utils import cst_now
from app.models.security_log import AISecurityLog
from app.models.room import Room

PRICE_MAX_FACTOR = 1.5
MAX_OPEN_WORK_ORDERS = 5


async def execute_security_guard(tool_name: str, user_role: str, params: dict, user_input: str = "", user_id: str = "") -> dict:
    """安全拦截器：Tool 调用前校验。返回 {"ok": True} 或 {"ok": False, "error": "..."}"""

    # ① modify_room_price_tool — 仅 manager + 涨幅 ≤ 50%
    if tool_name == "modify_room_price_tool":
        if user_role != "manager":
            await _log_violation(
                user_id=user_id,
                user_role=user_role,
                tool_name=tool_name,
                tool_params=params,
                violation_type="ROLE_VIOLATION",
                user_input=user_input,
            )
            return {"ok": False, "error": "权限不足，拒绝执行。仅店长(manager)可修改房价。"}

        room_type = params.get("room_type", "")
        new_price_yuan = params.get("new_price_yuan", 0)
        base_price = await _get_base_price(room_type)
        if base_price > 0 and new_price_yuan > base_price * PRICE_MAX_FACTOR / 100:
            await _log_violation(
                user_id=user_id,
                user_role=user_role,
                tool_name=tool_name,
                tool_params=params,
                violation_type="PRICE_LIMIT",
                user_input=user_input,
            )
            max_allowed = base_price * PRICE_MAX_FACTOR / 100
            return {"ok": False, "error": f"价格涨幅超过{PRICE_MAX_FACTOR*100:.0f}%上限。最大允许：¥{max_allowed:.0f}，请求：¥{new_price_yuan:.0f}"}

    # ② control_device_tool — 空调温度边界 [16, 30]
    if tool_name == "control_device_tool":
        if params.get("device") in ("ac_temp", "ac_temperature"):
            val = params.get("value", 24)
            if isinstance(val, (int, float)) and (val < 16 or val > 30):
                await _log_violation(
                    user_id=user_id,
                    user_role=user_role,
                    tool_name=tool_name,
                    tool_params=params,
                    violation_type="PARAM_ABUSE",
                    user_input=user_input,
                )
                return {"ok": False, "error": f"温度超出范围 16°C-30°C，请求：{val}°C"}

    # ③ create_work_order_tool — 单房间未结工单 ≤ 5
    if tool_name == "create_work_order_tool":
        open_count = await _count_open_orders(params.get("room_id"))
        if open_count >= MAX_OPEN_WORK_ORDERS:
            await _log_violation(
                user_id=user_id,
                user_role=user_role,
                tool_name=tool_name,
                tool_params=params,
                violation_type="LIMIT_EXCEEDED",
                user_input=user_input,
            )
            return {"ok": False, "error": f"该房间未结工单已达{MAX_OPEN_WORK_ORDERS}个上限，请等待现有工单完成后重试。"}

    return {"ok": True}


async def _log_violation(user_id: str, user_role: str, tool_name: str, tool_params: dict, violation_type: str, user_input: str):
    try:
        async with async_session() as db:
            log_entry = AISecurityLog(
                user_id=uuid.UUID(user_id) if user_id else None,
                user_type="guest" if user_role == "guest" else "staff",
                role=user_role,
                tool_name=tool_name,
                tool_params=tool_params,
                violation_type=violation_type,
                user_input=user_input,
                intercepted_at=cst_now(),
            )
            db.add(log_entry)
            await db.commit()
    except Exception:
        pass


async def _get_base_price(room_type: str) -> int:
    from sqlmodel import select
    async with async_session() as db:
        result = await db.execute(select(Room.base_price).where(Room.room_type == room_type).limit(1))
        val = result.scalar_one_or_none()
        return val or 0


async def _count_open_orders(room_id: str | None) -> int:
    if not room_id:
        return 0
    from sqlmodel import select, func
    from app.models.work_order import WorkOrder
    async with async_session() as db:
        result = await db.execute(
            select(func.count()).where(
                WorkOrder.room_id == uuid.UUID(str(room_id)),
                WorkOrder.status.in_(["submitted", "accepted", "processing"]),
            )
        )
        return result.scalar() or 0
