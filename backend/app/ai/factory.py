from app.ai.base import AIProvider
from app.ai.free_api_provider import FreeAPIProvider
from app.ai.gemini_provider import GeminiProvider
from app.ai.local_provider import LocalProvider
from app.ai.mock_provider import MockProvider
from app.ai.openai_provider import OpenAIProvider

_PROVIDERS: dict[str, type[AIProvider]] = {
    "demo": MockProvider,
    "local": LocalProvider,
    "free_api": FreeAPIProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
}


def available_provider_names() -> list[str]:
    return list(_PROVIDERS.keys())


def get_provider(name: str) -> AIProvider:
    provider_cls = _PROVIDERS.get(name, MockProvider)
    return provider_cls()
