import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel

from app.core.utils import cst_now


class InvoiceRecord(SQLModel, table=True):
    __tablename__ = "invoice_records"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    order_id: uuid.UUID = Field(foreign_key="orders.id")
    company_name: str = Field(max_length=100)
    tax_id: str = Field(max_length=30)
    email: str = Field(max_length=100)
    status: str = Field(default="draft", max_length=20)
    created_at: datetime = Field(default_factory=cst_now)
