import uuid
from typing import Optional
from pydantic import BaseModel, field_serializer


class RoomBase(BaseModel):
    room_number: str
    room_type: str
    base_price: int
    current_price: int
    floor: int = 1


class RoomResponse(RoomBase):
    id: uuid.UUID
    status: str
    device_states: Optional[dict] = None

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, value: uuid.UUID) -> str:
        return str(value)


class DeviceControl(BaseModel):
    device: str
    state: dict


class RoomStatusUpdate(BaseModel):
    status: str
