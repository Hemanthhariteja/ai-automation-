import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest

from app.ai.base import AIProviderError, ExtractedInfo, IntentClassification
from app.ai.free_api_provider import FreeAPIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.local_provider import LocalProvider
from app.ai.openai_provider import OpenAIProvider

REAL_PROVIDERS = [LocalProvider, FreeAPIProvider, OpenAIProvider, GeminiProvider]


@pytest.mark.parametrize("provider_cls", REAL_PROVIDERS)
def test_check_connection_never_raises(provider_cls):
    provider = provider_cls()
    ok, message = provider.check_connection()
    assert isinstance(ok, bool)
    assert isinstance(message, str) and message


@pytest.mark.parametrize("provider_cls", REAL_PROVIDERS)
def test_without_config_every_capability_raises_a_clean_provider_error(provider_cls):
    """None of these have real API keys in the test environment, so every
    generation method should fail with a typed, catchable AIProviderError —
    never a raw exception the fallback chain couldn't recognize."""
    provider = provider_cls()
    classification = IntentClassification(intent="general_inquiry", category=None, confidence=0.5)
    extracted = ExtractedInfo()

    with pytest.raises(AIProviderError):
        provider.classify_intent("hello")
    with pytest.raises(AIProviderError):
        provider.extract_information("hello")
    with pytest.raises(AIProviderError):
        provider.score_lead(classification, extracted, "hello")
    with pytest.raises(AIProviderError):
        provider.generate_response({"name": "Test Co"}, "hello", extracted)
    with pytest.raises(AIProviderError):
        provider.summarize(["hello"])


@pytest.mark.parametrize("provider_cls", REAL_PROVIDERS)
def test_provider_error_names_the_provider(provider_cls):
    provider = provider_cls()
    try:
        provider.classify_intent("hello")
        pytest.fail("expected AIProviderError")
    except AIProviderError as exc:
        assert exc.provider == provider.name


def test_local_provider_reports_unreachable_without_ollama_running():
    provider = LocalProvider()
    ok, message = provider.check_connection()
    assert ok is False
    assert "ollama" in message.lower() or "reach" in message.lower()


def test_key_based_providers_report_missing_key():
    for provider_cls in [FreeAPIProvider, OpenAIProvider, GeminiProvider]:
        provider = provider_cls()
        ok, message = provider.check_connection()
        assert ok is False
        assert "not set" in message.lower()
