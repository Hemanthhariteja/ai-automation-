from typing import Optional

from pydantic import BaseModel, Field


class ProviderStatus(BaseModel):
    name: str
    label: str  # FREE | FREE-TIER | PAID
    connection_ok: bool
    message: str
    is_active_primary: bool
    is_active_fallback: bool


class AIStatusResponse(BaseModel):
    active_provider: str
    active_fallback: str
    providers: list[ProviderStatus]


class AISettingsUpdate(BaseModel):
    ai_provider: Optional[str] = None
    ai_fallback_provider: Optional[str] = None


class AITestRequest(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class AITestResponse(BaseModel):
    intent: str
    category: Optional[str]
    confidence: float
    extracted: dict
    score: int
    score_breakdown: dict
    response_text: str
    provider_used: str
    fallback_used: bool
    fallback_reason: Optional[str]
