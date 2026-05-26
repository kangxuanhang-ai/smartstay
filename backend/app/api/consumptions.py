import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.models.consumption import Consumption
from app.schemas.consumption import ConsumptionCreate, ConsumptionResponse

router = APIRouter(prefix="/api/consumptions", tags=["consumptions"])


@router.post("/", response_model=ConsumptionResponse)
async def create_consumption(
    req: ConsumptionCreate,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    c = Consumption(
        order_id=uuid.UUID(req.order_id),
        room_id=uuid.UUID(req.room_id),
        item_name=req.item_name,
        category=req.category,
        amount=req.amount,
        quantity=req.quantity,
        created_by="front_desk",
        consumed_at=datetime.utcnow(),
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return ConsumptionResponse(
        id=str(c.id),
        order_id=str(c.order_id) if c.order_id else None,
        room_id=str(c.room_id),
        item_name=c.item_name,
        category=c.category,
        amount=c.amount,
        quantity=c.quantity,
        consumed_at=c.consumed_at.isoformat() if c.consumed_at else None,
        created_by=c.created_by,
    )


@router.get("/{order_id}", response_model=list[ConsumptionResponse])
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
        ConsumptionResponse(
            id=str(c.id),
            order_id=str(c.order_id) if c.order_id else None,
            room_id=str(c.room_id),
            item_name=c.item_name,
            category=c.category,
            amount=c.amount,
            quantity=c.quantity,
            consumed_at=c.consumed_at.isoformat() if c.consumed_at else None,
            created_by=c.created_by,
        )
        for c in consumptions
    ]
