from typing import Any

from app.ai.base import (
    ExtractedInfo,
    GeneratedResponse,
    IntentClassification,
    LeadScoreResult,
    SummaryResult,
)
from app.ai.mock_provider import CATEGORY_KEYWORDS, INTENT_KEYWORDS

# Derived from the same dicts Demo Mode classifies with, so re-targeting the
# app at a different vertical still only means swapping those dicts.
VALID_INTENTS = frozenset(INTENT_KEYWORDS) | {"general_inquiry"}
VALID_CATEGORIES = frozenset(CATEGORY_KEYWORDS)
VALID_URGENCIES = frozenset({"high", "medium", "low"})

MAX_EXTRACTED_FIELD_CHARS = 500
MAX_GENERATED_TEXT_CHARS = 4000


class InvalidAIOutputError(ValueError):
    """A provider returned something that isn't usable — wrong type, a label
    outside the allowed set, an out-of-range number, empty text."""


def _is_real_number(value: Any) -> bool:
    # bool is a subclass of int, and True is never a meaningful score.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _validate_classification(result: IntentClassification) -> None:
    if result.intent not in VALID_INTENTS:
        raise InvalidAIOutputError(f"unknown intent {result.intent!r}")
    if result.category is not None and result.category not in VALID_CATEGORIES:
        raise InvalidAIOutputError(f"unknown category {result.category!r}")
    if not _is_real_number(result.confidence) or not 0.0 <= result.confidence <= 1.0:
        raise InvalidAIOutputError(f"confidence must be between 0 and 1, got {result.confidence!r}")


def _validate_extracted(result: ExtractedInfo) -> None:
    for field_name, value in result.to_dict().items():
        if value is None:
            continue
        if not isinstance(value, str):
            raise InvalidAIOutputError(f"extracted {field_name} must be text or null, got {type(value).__name__}")
        if len(value) > MAX_EXTRACTED_FIELD_CHARS:
            raise InvalidAIOutputError(f"extracted {field_name} is longer than {MAX_EXTRACTED_FIELD_CHARS} characters")
    if result.urgency is not None and result.urgency not in VALID_URGENCIES:
        raise InvalidAIOutputError(f"unknown urgency {result.urgency!r}")


def _validate_score(result: LeadScoreResult) -> None:
    if not isinstance(result.score, int) or isinstance(result.score, bool) or not 0 <= result.score <= 100:
        raise InvalidAIOutputError(f"score must be a whole number from 0 to 100, got {result.score!r}")
    if not isinstance(result.breakdown, dict):
        raise InvalidAIOutputError("score breakdown must be an object")


def _validate_text(text: Any, what: str) -> None:
    if not isinstance(text, str) or not text.strip():
        raise InvalidAIOutputError(f"{what} is empty")
    if len(text) > MAX_GENERATED_TEXT_CHARS:
        raise InvalidAIOutputError(f"{what} is longer than {MAX_GENERATED_TEXT_CHARS} characters")


def validate_result(result: Any) -> None:
    """Raise InvalidAIOutputError if a provider's result can't be trusted.
    Called by the fallback orchestrator on every result, so a provider that
    returns garbage is treated exactly like one that failed outright."""
    if isinstance(result, IntentClassification):
        _validate_classification(result)
    elif isinstance(result, ExtractedInfo):
        _validate_extracted(result)
    elif isinstance(result, LeadScoreResult):
        _validate_score(result)
    elif isinstance(result, GeneratedResponse):
        _validate_text(result.text, "generated response")
    elif isinstance(result, SummaryResult):
        _validate_text(result.summary, "summary")
    else:
        raise InvalidAIOutputError(f"unexpected result type {type(result).__name__}")
