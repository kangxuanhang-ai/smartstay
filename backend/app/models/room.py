import uuid
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class Room(SQLModel, table=True):
    __tablename__ = "rooms"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_number: str = Field(max_length=10, unique=True)
    room_type: str = Field(max_length=20)
    base_price: int
    current_price: int
    status: str = Field(max_length=20, default="vacant")
    device_states: Optional[dict] = Field(default_factory=dict, sa_column=Column(JSONB))
    floor: int = Field(default=1)
