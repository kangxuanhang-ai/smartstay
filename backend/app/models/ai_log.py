import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel, Column
from sqlalchemy.dialects.postgresql import JSONB


class AIPricingLog(SQLModel, table=True):
    __tablename__ = "ai_pricing_logs"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    room_type: str = Field(max_length=20)
    trigger_reason: str
    original_price: int
    suggested_price: int
    status: str = Field(default="pending", max_length=20)
    suggested_by: str = Field(default="AI \u00b7 \u5b9a\u4ef7Agent", max_length=50)
    confirmed_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = Field(default=None)


class AuditReport(SQLModel, table=True):
    __tablename__ = "audit_reports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    date: str
    content: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    anomalies: Optional[dict] = Field(default=None, sa_column=Column(JSONB))
    generated_at: datetime = Field(default_factory=datetime.utcnow)
