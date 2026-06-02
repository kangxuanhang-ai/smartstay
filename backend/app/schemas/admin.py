from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    name: str
    id_card: str
    phone: str = ""
    role: str = "front_desk"


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    role: str | None = None
