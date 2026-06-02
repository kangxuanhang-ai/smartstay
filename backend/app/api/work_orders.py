import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.utils import cst_now, cst_isoformat
from app.models.guest import Guest
from app.models.user import Staff
from app.models.order import Order
from app.models.room import Room
from app.models.work_order import WorkOrder
from app.schemas.work_order import WorkOrderCreate, WorkOrderAssign, WorkOrderResponse
from app.ws.manager import manager

router = APIRouter(prefix="/api/work-orders", tags=["work-orders"])


@router.get("/staff")
async def get_staff_list(
    work_order_type: str | None = None,
    current_user: Staff = Depends(require_role("front_desk", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """获取可指派员工列表。work_order_type=delivery→保洁，repair→维修"""
    staff_type_map = {"delivery": "housekeeping", "repair": "maintenance"}
    staff_type = staff_type_map.get(work_order_type) if work_order_type else None

    stmt = select(Staff).where(Staff.role == "front_desk", Staff.staff_type.isnot(None))
    if staff_type:
        stmt = stmt.where(Staff.staff_type == staff_type)
    result = await db.execute(stmt)
    staff_list = result.scalars().all()
    return [{"id": str(s.id), "name": s.name, "role": s.role, "staff_type": s.staff_type} for s in staff_list]


@router.post("/", response_model=WorkOrderResponse)
async def create_work_order(
    req: WorkOrderCreate,
    current_user: Guest | Staff = Depends(require_role("guest", "front_desk")),
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

    room_result = await db.execute(select(Room.room_number).where(Room.id == wo.room_id))
    room_number = room_result.scalar_one_or_none() or "?"
    await manager.broadcast_biz({
        "event": "work_order.new",
        "data": {
            "order_id": str(wo.id),
            "room_number": room_number,
            "type": wo.type,
            "content": wo.content,
        },
    })

    return wo


@router.get("/my-orders", response_model=list[WorkOrderResponse])
async def get_my_work_orders(
    current_user: Guest = Depends(require_role("guest")),
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


@router.get("/")
async def get_all_work_orders(
    page: int = 1,
    page_size: int = 50,
    current_user: Staff = Depends(require_role("front_desk", "manager")),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    result = await db.execute(
        select(WorkOrder).order_by(WorkOrder.created_at.desc()).offset(offset).limit(page_size)
    )
    orders = result.scalars().all()

    room_ids = {wo.room_id for wo in orders}
    room_map = {}
    if room_ids:
        room_result = await db.execute(select(Room).where(Room.id.in_(room_ids)))
        room_map = {str(r.id): r.room_number for r in room_result.scalars().all()}

    return [
        {
            "id": str(wo.id),
            "room_id": str(wo.room_id),
            "room_number": room_map.get(str(wo.room_id), "?"),
            "order_id": str(wo.order_id) if wo.order_id else None,
            "type": wo.type,
            "content": wo.content,
            "assigned_resource": wo.assigned_resource,
            "status": wo.status,
            "ai_generated": wo.ai_generated,
            "created_at": cst_isoformat(wo.created_at),
            "updated_at": cst_isoformat(wo.updated_at),
        }
        for wo in orders
    ]


@router.put("/{wo_id}/accept")
async def accept_work_order(
    wo_id: str,
    current_user: Staff = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    wo_result = await db.execute(select(WorkOrder).where(WorkOrder.id == uuid.UUID(wo_id)))
    wo = wo_result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    wo.status = "accepted"
    wo.updated_at = cst_now()
    await db.commit()

    guest_user_id = await _get_guest_user_id(db, wo.room_id)
    if guest_user_id:
        await manager.send_to_user(guest_user_id, {
            "event": "work_order.status_change",
            "data": {"order_id": wo_id, "new_status": "accepted", "message": "前台已接单"},
        })

    return {"message": "Work order accepted"}


@router.put("/{wo_id}/assign")
async def assign_work_order(
    wo_id: str,
    body: WorkOrderAssign,
    current_user: Staff = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    wo_result = await db.execute(select(WorkOrder).where(WorkOrder.id == uuid.UUID(wo_id)))
    wo = wo_result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    wo.assigned_resource = body.assigned_resource
    wo.status = "processing"
    wo.updated_at = cst_now()
    await db.commit()

    guest_user_id = await _get_guest_user_id(db, wo.room_id)
    if guest_user_id:
        await manager.send_to_user(guest_user_id, {
            "event": "work_order.status_change",
            "data": {"order_id": wo_id, "new_status": "processing", "message": f"保洁{body.assigned_resource}处理中"},
        })

    return {"message": f"Assigned to {body.assigned_resource}"}


@router.put("/{wo_id}/complete")
async def complete_work_order(
    wo_id: str,
    current_user: Staff = Depends(require_role("front_desk")),
    db: AsyncSession = Depends(get_db),
):
    wo_result = await db.execute(select(WorkOrder).where(WorkOrder.id == uuid.UUID(wo_id)))
    wo = wo_result.scalar_one_or_none()
    if not wo:
        raise HTTPException(status_code=404, detail="Work order not found")

    wo.status = "completed"
    wo.updated_at = cst_now()
    await db.commit()

    guest_user_id = await _get_guest_user_id(db, wo.room_id)
    if guest_user_id:
        await manager.send_to_user(guest_user_id, {
            "event": "work_order.status_change",
            "data": {"order_id": wo_id, "new_status": "completed", "message": "工单已完成/已送达"},
        })

    return {"message": "Work order completed"}


async def _get_guest_user_id(db: AsyncSession, room_id) -> str | None:
    """通过 room_id 查找当前入住的 guest user_id"""
    result = await db.execute(
        select(Order.user_id).where(
            Order.room_id == room_id,
            Order.status == "checked_in",
        ).limit(1)
    )
    user_id = result.scalar_one_or_none()
    return str(user_id) if user_id else None
