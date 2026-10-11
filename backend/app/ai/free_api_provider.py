from app.ai.base import (
    AIProvider,
    AIProviderError,
    ExtractedInfo,
    GeneratedResponse,
    IntentClassification,
    LeadScoreResult,
    SummaryResult,
)
from app.config import get_settings

settings = get_settings()


class FreeAPIProvider(AIProvider):
    """Hugging Face free-tier Inference API. Requires HUGGINGFACE_API_KEY.
    Prompt-based generation logic lands in a later phase; for now this
    provider reports whether a key is configured and fails cleanly onto the
    next link in the fallback chain."""

    name = "free_api"
    label = "FREE-TIER"

    def check_connection(self) -> tuple[bool, str]:
        if not settings.huggingface_api_key:
            return False, "HUGGINGFACE_API_KEY is not set"
        return True, "Hugging Face API key is configured"

    def _not_implemented(self) -> AIProviderError:
        return AIProviderError(
            "Hugging Face free-tier generation is not wired up yet (planned for a later phase)",
            provider=self.name,
        )

    def classify_intent(self, text: str) -> IntentClassification:
        raise self._not_implemented()

    def extract_information(self, text: str) -> ExtractedInfo:
        raise self._not_implemented()

    def score_lead(self, classification, extracted, text: str) -> LeadScoreResult:
        raise self._not_implemented()

    def generate_response(self, business_profile: dict, text: str, extracted: ExtractedInfo) -> GeneratedResponse:
        raise self._not_implemented()

    def summarize(self, messages: list[str]) -> SummaryResult:
        raise self._not_implemented()
