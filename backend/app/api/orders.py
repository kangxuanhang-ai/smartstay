import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.security import get_password_hash
from app.core.utils import cst_now, cst_isoformat
from app.models.guest import Guest
from app.models.user import Staff
from app.models.room import Room
from app.models.order import Order
from app.models.consumption import Consumption
from app.models.invoice import InvoiceRecord
from app.schemas.order import CheckInRequest, BillResponse, InvoiceRequest, OrderResponse, BillingLine
from app.ws.manager import manager

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/checkin")
async def check_in(
    req: CheckInRequest,
    current_user: Staff = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(select(Guest).where(Guest.id_card == req.id_card))
        guest = result.scalar_one_or_none()
        if not guest:
            guest = Guest(
                id_card=req.id_card,
                phone=req.phone,
                name=req.name,
                hashed_password=get_password_hash("123456"),
                is_first_login=True,
                is_active=True,
            )
            db.add(guest)
            await db.flush()
        else:
            guest.is_active = True
            db.add(guest)

        result = await db.execute(select(Room).where(Room.id == uuid.UUID(req.room_id)))
        room = result.scalar_one_or_none()
        if not room:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        if room.status != "vacant":
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not available")

        order = Order(
            user_id=guest.id,
            room_id=room.id,
            status="checked_in",
            source=req.source,
            total_amount=room.current_price,
            check_in_time=cst_now(),
        )
        db.add(order)
        room.status = "occupied"

        await db.commit()
        return {"message": "Check-in successful", "order_id": str(order.id), "guest_id": str(guest.id)}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise


@router.get("/current", response_model=OrderResponse)
async def get_current_order(
    current_user: Guest = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id, Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active order")
    return order


@router.get("/{order_id}/bill", response_model=BillResponse)
async def get_bill(order_id: str, current_user: Guest | Staff = Depends(require_role("guest", "front_desk", "manager")), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    result = await db.execute(select(Consumption).where(Consumption.order_id == order.id))
    consumptions = result.scalars().all()

    consumption_total = sum(c.amount * c.quantity for c in consumptions)
    lines = [
        BillingLine(
            item_name=c.item_name,
            category=c.category,
            amount=c.amount,
            quantity=c.quantity,
            consumed_at=c.consumed_at,
        )
        for c in consumptions
    ]

    return BillResponse(
        order_id=str(order.id),
        room_rate=order.total_amount,
        consumptions=lines,
        consumption_total=consumption_total,
        grand_total=order.total_amount + consumption_total,
        deposit_rate=1.0,
    )


@router.get("/room/{room_id}/active")
async def get_active_order_by_room(
    room_id: str,
    current_user: Staff = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order)
        .where(Order.room_id == uuid.UUID(room_id), Order.status == "checked_in")
        .order_by(Order.created_at.desc())
    )
    orders = result.scalars().all()
    if not orders:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active order for this room")
    order = orders[0]

    result_guest = await db.execute(select(Guest).where(Guest.id == order.user_id))
    guest = result_guest.scalar_one_or_none()

    return {
        "id": str(order.id),
        "room_id": str(order.room_id),
        "user_id": str(order.user_id),
        "status": order.status,
        "source": order.source,
        "check_in_time": cst_isoformat(order.check_in_time),
        "guest_name": guest.name if guest else None,
        "guest_id_card": guest.id_card if guest else None,
        "guest_phone": guest.phone if guest else None,
    }


@router.put("/{order_id}/checkout")
async def checkout(
    order_id: str,
    current_user: Staff = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(select(Order).where(Order.id == uuid.UUID(order_id)))
        order = result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
        if order.status != "checked_in":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Order not in checked_in status")

        order.status = "checked_out"
        order.check_out_time = cst_now()

        await db.execute(
            update(Room).where(Room.id == order.room_id).values(status="dirty")
        )

        result_guest = await db.execute(select(Guest).where(Guest.id == order.user_id))
        guest = result_guest.scalar_one_or_none()
        if guest:
            result_active = await db.execute(
                select(Order).where(
                    Order.user_id == order.user_id,
                    Order.status == "checked_in",
                    Order.id != order.id,
                )
            )
            remaining = result_active.scalars().all()
            if not remaining:
                guest.is_active = False
                db.add(guest)

        await db.commit()

        await manager.broadcast_biz({
            "event": "room.status_change",
            "data": {"room_id": str(order.room_id), "old_status": "occupied", "new_status": "dirty"},
        })

        return {"message": "Checkout successful"}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise


@router.put("/{order_id}/invoice")
async def submit_invoice(
    order_id: str,
    req: InvoiceRequest,
    current_user: Guest = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    # 校验订单属于当前用户
    result = await db.execute(
        select(Order).where(Order.id == uuid.UUID(order_id), Order.user_id == current_user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="订单不属于当前用户")

    record = InvoiceRecord(
        order_id=uuid.UUID(order_id),
        company_name=req.company_name,
        tax_id=req.tax_id,
        email=req.email,
        status="draft",
    )
    db.add(record)
    await db.commit()
    return {"message": "Invoice info saved", "id": str(record.id)}
