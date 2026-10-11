from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Resolved relative to this file so it finds the repo-root .env
    # regardless of the working directory the app is launched from.
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AI Small Business Automation Platform"
    environment: str = "development"
    debug: bool = True

    # Auth
    # Access tokens are short-lived and stateless (can't be revoked); the
    # refresh token is what actually gets invalidated on logout, stored
    # hashed and checked server-side. See app/models/refresh_token.py.
    secret_key: str = "dev-only-secret-change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "sqlite:///./app.db"

    # AI provider selection (see app/ai/ for the provider abstraction)
    ai_provider: str = "demo"  # demo | local | free_api | openai | gemini
    ai_fallback_provider: str = "demo"

    openai_api_key: str = ""
    gemini_api_key: str = ""
    huggingface_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # AI call safety limits
    ai_request_timeout_seconds: int = 15
    ai_max_retries: int = 1
    ai_max_input_chars: int = 4000
    ai_max_output_tokens: int = 512

    # CORS — comma-separated for a deployed frontend + local dev at once,
    # e.g. "http://localhost:5173,https://my-demo.vercel.app"
    frontend_origin: str = "http://localhost:5173"

    # Messenger/Instagram channel (Meta) — optional, never required. The
    # inbound webhook works with none of these set (see app/channels/mock.py
    # for the zero-setup simulate path); they're only needed to receive real
    # messages from a real Meta Page.
    facebook_verify_token: str = ""  # arbitrary string you choose, entered in Meta's webhook setup
    facebook_page_access_token: str = ""  # from the Meta Business/Developer console
    facebook_app_secret: str = ""  # used to verify the webhook's X-Hub-Signature-256; skipped if blank

    # Deployment
    # Free-tier hosts (e.g. Render) often use ephemeral disk — the SQLite file
    # resets on every redeploy/restart. Auto-seeding on an empty DB turns that
    # into a feature for a public demo link instead of a broken-looking blank
    # app. Off by default; never enable this against a real database.
    auto_seed_demo_data: bool = False

    @property
    def frontend_origins(self) -> list[str]:
        return [origin.strip() for origin in self.frontend_origin.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
