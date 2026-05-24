import uuid
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.models.consumption import Consumption

router = APIRouter(prefix="/api/consumptions", tags=["consumptions"])


@router.post("/")
async def create_consumption(
    body: dict,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    c = Consumption(
        order_id=uuid.UUID(body["order_id"]) if body.get("order_id") else None,
        room_id=uuid.UUID(body["room_id"]),
        item_name=body["item_name"],
        category=body.get("category", "other"),
        amount=body["amount"],
        quantity=body.get("quantity", 1),
        created_by="front_desk",
        consumed_at=datetime.utcnow(),
    )
    db.add(c)
    await db.commit()
    return {"message": "消费记录已挂账成功", "id": str(c.id)}


@router.get("/{order_id}")
async def get_order_consumptions(
    order_id: str,
    current_user: User = Depends(require_role("front_desk", "manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Consumption).where(Consumption.order_id == uuid.UUID(order_id))
    )
    consumptions = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "order_id": str(c.order_id) if c.order_id else None,
            "room_id": str(c.room_id),
            "item_name": c.item_name,
            "category": c.category,
            "amount": c.amount,
            "quantity": c.quantity,
            "consumed_at": c.consumed_at.isoformat() if c.consumed_at else None,
            "created_by": c.created_by,
        }
        for c in consumptions
    ]
