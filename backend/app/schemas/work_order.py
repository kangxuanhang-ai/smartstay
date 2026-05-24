import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_serializer


class WorkOrderCreate(BaseModel):
    room_id: str
    type: str
    content: str


class WorkOrderAssign(BaseModel):
    assigned_resource: str


class WorkOrderResponse(BaseModel):
    id: uuid.UUID
    room_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    type: str
    content: str
    assigned_resource: Optional[str] = None
    status: str
    ai_generated: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("id", "room_id", "order_id")
    def serialize_uuid(self, value: uuid.UUID) -> str:
        return str(value)
