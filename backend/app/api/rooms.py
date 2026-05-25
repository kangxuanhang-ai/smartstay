import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update

from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.models.user import User
from app.models.room import Room
from app.models.order import Order
from app.schemas.room import RoomResponse, DeviceControl, RoomStatusUpdate

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


@router.get("/my-room", response_model=RoomResponse)
async def get_my_room(
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id, Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active check-in found")

    result = await db.execute(select(Room).where(Room.id == order.room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


@router.post("/my-room/device")
async def control_device(
    control: DeviceControl,
    current_user: User = Depends(require_role("guest")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Order).where(Order.user_id == current_user.id, Order.status == "checked_in")
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active check-in")

    result = await db.execute(select(Room).where(Room.id == order.room_id))
    room = result.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    device_states = room.device_states or {}
    device_states[control.device] = control.state

    await db.execute(
        update(Room).where(Room.id == room.id).values(device_states=device_states)
    )
    await db.commit()
    return {"message": f"{control.device} updated", "state": control.state}


@router.get("/", response_model=list[RoomResponse])
async def get_all_rooms(
    current_user: User = Depends(require_role("front_desk", "manager", "admin")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Room).order_by(Room.room_number))
    return result.scalars().all()


@router.put("/{room_id}/status")
async def update_room_status(
    room_id: str,
    body: RoomStatusUpdate,
    current_user: User = Depends(require_role("front_desk", "admin")),
    db: AsyncSession = Depends(get_db),
):
    valid_statuses = {"vacant", "occupied", "dirty", "maintenance"}
    if body.status not in valid_statuses:
        from fastapi import HTTPException as E
        raise E(status_code=400, detail=f"无效状态，仅支持: {valid_statuses}")
    await db.execute(
        update(Room).where(Room.id == uuid.UUID(room_id)).values(status=body.status)
    )
    await db.commit()
    return {"message": f"Room {room_id} status changed to {body.status}"}
