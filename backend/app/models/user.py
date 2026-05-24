import uuid
from datetime import datetime, timezone
from sqlmodel import Field, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    id_card: str = Field(max_length=18, unique=True, index=True)
    phone: str = Field(max_length=11)
    name: str = Field(max_length=50)
    hashed_password: str = Field(max_length=255)
    is_first_login: bool = Field(default=True)
    role: str = Field(max_length=20, default="guest")
    created_at: datetime = Field(default_factory=datetime.utcnow)
