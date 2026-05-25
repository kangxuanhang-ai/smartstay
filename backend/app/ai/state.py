from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import MessagesState


class AgentState(MessagesState):
    user_id: str
    room_id: Optional[str]
    order_id: Optional[str]
    role: str
    intent: str
    business_cards: list
