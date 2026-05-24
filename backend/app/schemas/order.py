import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, field_serializer


class CheckInRequest(BaseModel):
    id_card: str
    phone: str
    name: str
    room_id: str
    source: str = "self_app"


class BillingLine(BaseModel):
    item_name: str
    category: str
    amount: int
    quantity: int
    consumed_at: datetime


class BillResponse(BaseModel):
    order_id: uuid.UUID
    room_rate: int
    consumptions: list[BillingLine]
    consumption_total: int
    grand_total: int
    deposit_rate: float

    @field_serializer("order_id")
    def serialize_order_id(self, value: uuid.UUID) -> str:
        return str(value)


class InvoiceRequest(BaseModel):
    company_name: str
    tax_id: str
    email: str


class OrderResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    room_id: uuid.UUID
    status: str
    source: str
    total_amount: int
    check_in_time: Optional[datetime] = None
    check_out_time: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("id", "user_id", "room_id")
    def serialize_uuid(self, value: uuid.UUID) -> str:
        return str(value)
