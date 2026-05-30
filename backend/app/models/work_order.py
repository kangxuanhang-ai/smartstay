import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

from app.core.utils import cst_now


class WorkOrder(SQLModel, table=True):
    __tablename__ = "work_orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_id: uuid.UUID = Field(foreign_key="rooms.id")
    order_id: Optional[uuid.UUID] = Field(default=None, foreign_key="orders.id")
    type: str = Field(max_length=20)
    content: str
    assigned_resource: Optional[str] = Field(default=None, max_length=50)
    status: str = Field(max_length=20, default="submitted")
    ai_generated: bool = Field(default=False)
    created_at: datetime = Field(default_factory=cst_now)
    updated_at: Optional[datetime] = Field(default=None)
