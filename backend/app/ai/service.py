import time
from typing import Callable, Optional, TypeVar

from sqlalchemy.orm import Session

from app.ai.base import (
    AIProvider,
    AIProviderError,
    ExtractedInfo,
    GeneratedResponse,
    IntentClassification,
    LeadScoreResult,
    SummaryResult,
)
from app.ai.factory import get_provider
from app.ai.validation import InvalidAIOutputError, validate_result
from app.config import get_settings
from app.models.ai_log import AILog
from app.models.business import Business

settings = get_settings()

T = TypeVar("T")


class AllProvidersFailedError(Exception):
    """Should not happen in practice — Demo Mode is always last in the chain
    and never fails — but handled explicitly rather than letting a caller
    hit an unhandled exception."""


class AIService:
    """The fallback orchestrator: tries the business's configured provider,
    then its configured fallback, then Demo Mode, stopping at the first
    success. A result that fails validation (see app/ai/validation.py) counts
    as a failure, same as an exception. Every attempt (success or failure)
    is written to ai_logs as its own row, so the audit trail always shows
    which provider actually served a request and why each earlier one didn't."""

    def __init__(self, db: Session):
        self.db = db

    def resolve_provider_chain(self, business: Business) -> list[str]:
        primary = business.ai_provider or settings.ai_provider
        fallback = business.ai_fallback_provider or settings.ai_fallback_provider
        chain = [primary]
        if fallback and fallback not in chain:
            chain.append(fallback)
        if "demo" not in chain:
            chain.append("demo")
        return chain

    def _log(
        self,
        business_id: int,
        lead_id: Optional[int],
        operation: str,
        requested_provider: str,
        actual_provider: str,
        fallback_used: bool,
        fallback_reason: Optional[str],
        input_snippet: str,
        output: Optional[dict],
        success: bool,
        error_message: Optional[str],
        latency_ms: int,
    ) -> None:
        entry = AILog(
            business_id=business_id,
            lead_id=lead_id,
            operation=operation,
            requested_provider=requested_provider,
            actual_provider=actual_provider,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason[:300] if fallback_reason else None,  # column is String(300)
            input_snippet=input_snippet[: settings.ai_max_input_chars],
            output=output,
            success=success,
            error_message=error_message,
            latency_ms=latency_ms,
        )
        self.db.add(entry)
        self.db.commit()

    def _run(
        self,
        business: Business,
        operation: str,
        lead_id: Optional[int],
        input_snippet: str,
        call: Callable[[AIProvider], T],
        output_to_dict: Callable[[T], dict],
    ) -> tuple[T, str, bool, Optional[str]]:
        chain = self.resolve_provider_chain(business)
        requested = chain[0]
        last_error: Optional[str] = None

        for idx, provider_name in enumerate(chain):
            provider = get_provider(provider_name)
            fallback_used = idx > 0
            started = time.monotonic()
            error: Optional[str] = None
            result = None
            try:
                result = call(provider)
                validate_result(result)
            except AIProviderError as exc:
                error = f"{exc.provider}: {exc.message}"
            except InvalidAIOutputError as exc:
                error = f"{provider_name}: returned invalid output — {exc}"
            except Exception as exc:  # provider bugs must never crash the app
                error = f"{provider_name}: unexpected error — {exc}"

            # last_error is still the previous provider's failure here, i.e.
            # the reason this provider was tried at all (None for the first).
            self._log(
                business_id=business.id,
                lead_id=lead_id,
                operation=operation,
                requested_provider=requested,
                actual_provider=provider_name,
                fallback_used=fallback_used,
                fallback_reason=last_error,
                input_snippet=input_snippet,
                output=output_to_dict(result) if error is None else None,
                success=error is None,
                error_message=error,
                latency_ms=int((time.monotonic() - started) * 1000),
            )
            if error is None:
                return result, provider_name, fallback_used, last_error
            last_error = error

        # Every provider in the chain failed, including Demo Mode — should be
        # unreachable in practice. Each failed attempt is already in ai_logs,
        # so this surfaces the last error rather than crashing.
        raise AllProvidersFailedError(last_error or "All configured AI providers failed")

    def classify_intent(
        self, business: Business, text: str, lead_id: Optional[int] = None
    ) -> tuple[IntentClassification, str, bool, Optional[str]]:
        clipped = text[: settings.ai_max_input_chars]
        return self._run(
            business,
            "classify",
            lead_id,
            clipped,
            lambda p: p.classify_intent(clipped),
            lambda r: {"intent": r.intent, "category": r.category, "confidence": r.confidence},
        )

    def extract_information(
        self, business: Business, text: str, lead_id: Optional[int] = None
    ) -> tuple[ExtractedInfo, str, bool, Optional[str]]:
        clipped = text[: settings.ai_max_input_chars]
        return self._run(
            business, "extract", lead_id, clipped, lambda p: p.extract_information(clipped), lambda r: r.to_dict()
        )

    def score_lead(
        self,
        business: Business,
        classification: IntentClassification,
        extracted: ExtractedInfo,
        text: str,
        lead_id: Optional[int] = None,
    ) -> tuple[LeadScoreResult, str, bool, Optional[str]]:
        clipped = text[: settings.ai_max_input_chars]
        return self._run(
            business,
            "score",
            lead_id,
            clipped,
            lambda p: p.score_lead(classification, extracted, clipped),
            lambda r: {"score": r.score, "breakdown": r.breakdown},
        )

    def generate_response(
        self,
        business: Business,
        business_profile: dict,
        text: str,
        extracted: ExtractedInfo,
        lead_id: Optional[int] = None,
    ) -> tuple[GeneratedResponse, str, bool, Optional[str]]:
        clipped = text[: settings.ai_max_input_chars]
        return self._run(
            business,
            "generate_response",
            lead_id,
            clipped,
            lambda p: p.generate_response(business_profile, clipped, extracted),
            lambda r: {"text": r.text},
        )

    def summarize(
        self, business: Business, messages: list[str], lead_id: Optional[int] = None
    ) -> tuple[SummaryResult, str, bool, Optional[str]]:
        joined = " | ".join(messages)[: settings.ai_max_input_chars]
        return self._run(
            business,
            "summarize",
            lead_id,
            joined,
            lambda p: p.summarize(messages),
            lambda r: {"summary": r.summary},
        )
