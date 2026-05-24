import uuid
from pydantic import BaseModel, field_serializer


class LoginRequest(BaseModel):
    id_card: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


class UserInfo(BaseModel):
    id: uuid.UUID
    id_card: str
    phone: str
    name: str
    role: str
    is_first_login: bool

    model_config = {"from_attributes": True}

    @field_serializer("id")
    def serialize_id(self, value: uuid.UUID) -> str:
        return str(value)
