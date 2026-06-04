import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

from app.core.utils import cst_now


class GuestPreference(SQLModel, table=True):
    __tablename__ = "guest_preferences"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    guest_id: uuid.UUID = Field(foreign_key="guests.id", index=True)
    key: str = Field(max_length=50)  # ac_temp, curtain, bedside_light, bedroom_light, living_light, ac_mode
    value: str = Field(max_length=20)
    updated_at: datetime = Field(default_factory=cst_now)