import httpx

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


class LocalProvider(AIProvider):
    """Runs against a local Ollama instance. Needs Ollama installed and
    running separately — entirely free, but not bundled with this app, so
    it's optional. Prompt-based classify/extract/score/generate logic lands
    in a later phase; for now this provider proves out connection checking
    and fails cleanly (never crashes) so the fallback chain can take over."""

    name = "local"
    label = "FREE"

    def check_connection(self) -> tuple[bool, str]:
        try:
            response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=0.3)
            if response.status_code == 200:
                return True, f"Connected to Ollama at {settings.ollama_base_url}"
            return False, f"Ollama responded with status {response.status_code}"
        except httpx.RequestError as exc:
            return False, f"Could not reach Ollama at {settings.ollama_base_url}: {exc}"

    def _not_implemented(self) -> AIProviderError:
        return AIProviderError(
            "Local Ollama generation is not wired up yet (planned for a later phase)", provider=self.name
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
