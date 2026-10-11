import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: str
    content: str
    created_at: datetime.datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lead_id: Optional[int]
    channel: str
    summary: Optional[str]
    messages: list[MessageResponse]


class GenerateResponseResult(BaseModel):
    conversation_id: int
    message: MessageResponse
    provider_used: str
    fallback_used: bool
    fallback_reason: Optional[str]


class SummarizeResult(BaseModel):
    conversation_id: int
    summary: str
    provider_used: str
    fallback_used: bool
    fallback_reason: Optional[str]
