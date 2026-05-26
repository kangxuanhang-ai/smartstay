from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    name: str
    id_card: str
    phone: str = ""
    role: str = "front_desk"
