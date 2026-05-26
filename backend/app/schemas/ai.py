from pydantic import BaseModel
from typing import Optional


class ChatRequest(BaseModel):
    message: str


class SafetyThresholdRequest(BaseModel):
    threshold: int = 50
