import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel

from app.core.utils import cst_now


class Consumption(SQLModel, table=True):
    __tablename__ = "consumptions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="orders.id")
    room_id: uuid.UUID = Field(foreign_key="rooms.id")
    item_name: str = Field(max_length=100)
    category: str = Field(max_length=20)
    amount: int
    quantity: int = Field(default=1)
    consumed_at: datetime = Field(default_factory=cst_now)
    created_by: str = Field(default="guest", max_length=20)
