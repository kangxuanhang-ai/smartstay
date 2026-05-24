import uuid
from datetime import time
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class HotelInfo(SQLModel, table=True):
    __tablename__ = "hotel_info"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=100)
    address: str = Field(max_length=200)
    phone: str = Field(max_length=20)
    map_lat: float = Field(default=0.0)
    map_lng: float = Field(default=0.0)
    description: Optional[str] = Field(default=None)
    banner_images: Optional[dict] = Field(default=None, sa_column=Column(JSONB))


class Facility(SQLModel, table=True):
    __tablename__ = "facilities"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=50)
    type: str = Field(max_length=20)
    open_time: Optional[time] = Field(default=None)
    close_time: Optional[time] = Field(default=None)
    is_free: bool = Field(default=True)
    price: Optional[int] = Field(default=None)
    dynamic_tip: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
