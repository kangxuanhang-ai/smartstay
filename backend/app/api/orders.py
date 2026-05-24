import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.security import get_password_hash
from app.models.user import User
from app.models.room import Room
from app.models.order import Order
from app.models.consumption import Consumption
from app.models.invoice import InvoiceRecord
from app.schemas.order import CheckInRequest, BillResponse, InvoiceRequest, OrderResponse, BillingLine

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("/checkin")
async def check_in(
    req: CheckInRequest,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    try:
        result = await db.execute(select(User).where(User.id_card == req.id_card))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                id_card=req.id_card,
                phone=req.phone,
                name=req.name,
                hashed_password=get_password_hash("123456"),
                is_first_login=True,
                role="guest",
            )
            db.add(user)
            await db.flush()

        result = await db.execute(select(Room).where(Room.id == uuid.UUID(req.room_id)))
        room = result.scalar_one_or_none()
        if not room:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
        if room.status != "vacant":
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not available")

        order = Order(
            user_id=user.id,
            room_id=room.id,
            status="checked_in",
            source=req.source,
            total_amount=room.current_price,
            check_in_time=datetime.utcnow(),
        )
        db.add(order)
        room.status = "occupied"

        await db.commit()
        return {"message": "Check-in successful", "order_id": str(order.id)}
    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        raise


@router.get("/current", response_model=OrderResponse)
async def get_current_order(
    current_user: User = Depends(require_role("guest")),
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
async def get_bill(order_id: str, db: AsyncSession = Depends(get_db)):
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
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.room_id == uuid.UUID(room_id), Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active order for this room")
    return {"id": str(order.id), "room_id": str(order.room_id), "user_id": str(order.user_id), "status": order.status, "source": order.source, "check_in_time": order.check_in_time.isoformat() if order.check_in_time else None}


@router.put("/{order_id}/checkout")
async def checkout(
    order_id: str,
    current_user: User = Depends(require_role("front_desk")),
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
        order.check_out_time = datetime.utcnow()

        await db.execute(
            update(Room).where(Room.id == order.room_id).values(status="dirty")
        )
        await db.commit()
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
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
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
