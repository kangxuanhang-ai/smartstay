import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.models.order import Order
from app.models.work_order import WorkOrder
from app.schemas.work_order import WorkOrderCreate, WorkOrderAssign, WorkOrderResponse

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


@router.post("/", response_model=WorkOrderResponse)
async def create_work_order(
    req: WorkOrderCreate,
    current_user: User = Depends(require_role("guest", "front_desk")),
    db: AsyncSession = Depends(get_db),
):
    wo = WorkOrder(
        room_id=uuid.UUID(req.room_id),
        type=req.type,
        content=req.content,
        status="submitted",
        ai_generated=True,
    )
    db.add(wo)
    await db.commit()
    await db.refresh(wo)
    return wo


@router.get("/my-orders", response_model=list[WorkOrderResponse])
async def get_my_work_orders(
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id, Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        return []

    result = await db.execute(
        select(WorkOrder)
        .where(WorkOrder.room_id == order.room_id)
        .order_by(WorkOrder.created_at.desc())
    )
    return result.scalars().all()


@router.get("/", response_model=list[WorkOrderResponse])
async def get_all_work_orders(
    current_user: User = Depends(require_role("front_desk", "manager")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(WorkOrder).order_by(WorkOrder.created_at.desc()))
    return result.scalars().all()


@router.put("/{wo_id}/accept")
async def accept_work_order(
    wo_id: str,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(WorkOrder)
        .where(WorkOrder.id == uuid.UUID(wo_id), WorkOrder.status == "submitted")
        .values(status="accepted", updated_at=datetime.utcnow())
    )
    await db.commit()
    return {"message": "Work order accepted"}


@router.put("/{wo_id}/assign")
async def assign_work_order(
    wo_id: str,
    body: WorkOrderAssign,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(WorkOrder)
        .where(WorkOrder.id == uuid.UUID(wo_id))
        .values(
            assigned_resource=body.assigned_resource,
            status="processing",
            updated_at=datetime.utcnow(),
        )
    )
    await db.commit()
    return {"message": f"Assigned to {body.assigned_resource}"}


@router.put("/{wo_id}/complete")
async def complete_work_order(
    wo_id: str,
    current_user: User = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        update(WorkOrder)
        .where(WorkOrder.id == uuid.UUID(wo_id))
        .values(status="completed", updated_at=datetime.utcnow())
    )
    await db.commit()
    return {"message": "Work order completed"}
