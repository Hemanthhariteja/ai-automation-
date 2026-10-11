from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IntentClassification:
    intent: str
    category: Optional[str]
    confidence: float


@dataclass
class ExtractedInfo:
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    product_or_service: Optional[str] = None
    budget: Optional[str] = None
    location: Optional[str] = None
    requirement: Optional[str] = None
    urgency: Optional[str] = None
    preferred_date: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "product_or_service": self.product_or_service,
            "budget": self.budget,
            "location": self.location,
            "requirement": self.requirement,
            "urgency": self.urgency,
            "preferred_date": self.preferred_date,
        }


@dataclass
class LeadScoreResult:
    score: int  # 0-100: 0-30 low / 31-70 medium / 71-100 high. Not a validated statistical model.
    breakdown: dict = field(default_factory=dict)


@dataclass
class GeneratedResponse:
    text: str


@dataclass
class SummaryResult:
    summary: str


class AIProviderError(Exception):
    """Raised when a provider cannot fulfill a request — missing key, network
    error, timeout, rate limit, not-yet-implemented, etc. Always caught by the
    fallback orchestrator in app/ai/service.py; never left to bubble up
    as an unhandled exception."""

    def __init__(self, message: str, provider: str):
        super().__init__(message)
        self.provider = provider
        self.message = message


class AIProvider(ABC):
    """Common interface every provider implements. The rest of the app calls
    these methods and never needs to know which concrete provider is behind
    them — that's what makes providers swappable at runtime."""

    name: str = "base"
    label: str = "UNLABELED"  # FREE | FREE-TIER | PAID, shown in the settings UI

    @abstractmethod
    def check_connection(self) -> tuple[bool, str]:
        """Return (ok, message) describing reachability. Must never raise."""

    @abstractmethod
    def classify_intent(self, text: str) -> IntentClassification: ...

    @abstractmethod
    def extract_information(self, text: str) -> ExtractedInfo: ...

    @abstractmethod
    def score_lead(
        self, classification: IntentClassification, extracted: ExtractedInfo, text: str
    ) -> LeadScoreResult: ...

    @abstractmethod
    def generate_response(
        self, business_profile: dict, text: str, extracted: ExtractedInfo
    ) -> GeneratedResponse: ...

    @abstractmethod
    def summarize(self, messages: list[str]) -> SummaryResult: ...
