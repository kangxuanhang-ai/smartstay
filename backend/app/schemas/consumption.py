from pydantic import BaseModel
from typing import Optional


class ConsumptionCreate(BaseModel):
    order_id: str
    room_id: str
    item_name: str
    category: str = "other"
    amount: int
    quantity: int = 1


class ConsumptionResponse(BaseModel):
    id: str
    order_id: Optional[str] = None
    room_id: str
    item_name: str
    category: str
    amount: int
    quantity: int
    consumed_at: Optional[str] = None
    created_by: Optional[str] = None
