import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel

from app.core.utils import cst_now


class Staff(SQLModel, table=True):
    __tablename__ = "staff"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_card: str = Field(max_length=18, unique=True, index=True)
    phone: str = Field(max_length=11)
    name: str = Field(max_length=50)
    hashed_password: str = Field(max_length=255)
    is_first_login: bool = Field(default=True)
    is_active: bool = Field(default=True)
    role: str = Field(max_length=20)  # front_desk / manager / admin
    staff_type: Optional[str] = Field(default=None, max_length=20)  # housekeeping / maintenance
    created_at: datetime = Field(default_factory=cst_now)
