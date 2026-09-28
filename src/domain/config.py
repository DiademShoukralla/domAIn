from functools import cached_property, lru_cache
from uuid import UUID

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_base_url: str = "http://localhost:8000"
    default_user_id: UUID = Field(default=UUID("00000000-0000-4000-8000-000000000001"))

    database_url: str = "postgresql+asyncpg://domain:domain@localhost:5432/domain"

    token_encryption_key: str = ""

    bootstrap_api_key: str = "dev-api-key-change-me"

    github_app_oauth_client_id: str = ""
    github_app_oauth_client_secret: str = ""
    github_auth_redirect_uri: str = "http://localhost:8000/auth/github/callback"
    auth_allowed_github_ids: str = ""
    session_secret: str = "dev-session-secret-change-me"
    session_cookie_name: str = "domain_session"
    session_ttl_days: int = 30
    auth_display_cookie_name: str = "domain_auth_display"
    ws_allowed_origins: str = ""

    github_app_id: str = ""
    github_app_slug: str = ""
    github_app_private_key_base64: str = ""

    linear_client_id: str = ""
    linear_client_secret: str = ""
    linear_redirect_uri: str = "http://localhost:8000/oauth/linear/callback"
    linear_scopes: str = "read write"

    voyage_api_key: str = ""
    voyage_base_url: str = ""
    voyage_model: str = "voyage-context-4"
    embedding_dimensions: int = 1024

    rrf_k: int = 60
    retrieval_top_k: int = 10
    coverage_min_score: float = 0.3

    chunk_target_tokens: int = 512
    chunk_overlap_tokens: int = 50

    anthropic_api_key: str = ""
    supervisor_model: str = "anthropic:claude-haiku-4-5"
    retrieval_answer_model: str = "anthropic:claude-sonnet-5"
    persona_model: str = "anthropic:claude-sonnet-5"
    council_chair_model: str = "anthropic:claude-sonnet-5"

    @cached_property
    def allowed_github_ids(self) -> frozenset[int]:
        raw = self.auth_allowed_github_ids.strip()
        if not raw:
            return frozenset()
        return frozenset(int(part.strip()) for part in raw.split(",") if part.strip())

    @cached_property
    def ws_allowed_origin_set(self) -> frozenset[str]:
        raw = self.ws_allowed_origins.strip()
        if raw:
            return frozenset(part.strip().rstrip("/") for part in raw.split(",") if part.strip())
        base = self.app_base_url.rstrip("/")
        return frozenset({base})


@lru_cache
def get_settings() -> Settings:
    return Settings()
