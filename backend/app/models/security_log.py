import uuid
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB

from app.core.utils import cst_now


class AISecurityLog(SQLModel, table=True):
    __tablename__ = "ai_security_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID
    user_type: str = Field(max_length=20, default="guest")  # guest / staff
    room_id: Optional[uuid.UUID] = Field(default=None, foreign_key="rooms.id")
    role: str = Field(max_length=20)
    tool_name: str = Field(max_length=100)
    tool_params: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    violation_type: str = Field(max_length=50)
    user_input: Optional[str] = Field(default=None)
    intercepted_at: datetime = Field(default_factory=cst_now)
