from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str
    new_session: bool = False
    web_search: bool = False


class SafetyThresholdRequest(BaseModel):
    threshold: int = 50
