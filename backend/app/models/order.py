import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class Order(SQLModel, table=True):
    __tablename__ = "orders"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="guests.id")
    room_id: uuid.UUID = Field(foreign_key="rooms.id")
    status: str = Field(max_length=20, default="pending")
    check_in_time: Optional[datetime] = Field(default=None)
    check_out_time: Optional[datetime] = Field(default=None)
    total_amount: int = Field(default=0)
    source: str = Field(max_length=20, default="self_app")
    created_at: datetime = Field(default_factory=datetime.utcnow)
