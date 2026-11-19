from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_WEAK_MARKERS = ("change", "secret", "password", "example", "xxxx", "your")


def _split(value: object) -> object:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


class Settings(BaseSettings):
    """Application settings, read from environment variables (and `.env` in development)."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

    PROJECT_NAME: str = "AI-Finance-OS"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "test", "production"] = "production"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ENABLE_DOCS: bool = False

    # Signing key for access tokens. The algorithm is pinned to HS256 in code.
    SECRET_KEY: SecretStr
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=240)
    PASSWORD_RESET_EXPIRE_MINUTES: int = Field(default=30, ge=5, le=120)

    DATABASE_URL: SecretStr

    CORS_ORIGINS: Annotated[list[str], NoDecode] = Field(default_factory=list)
    ALLOWED_HOSTS: Annotated[list[str], NoDecode] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    MAX_BODY_BYTES: int = Field(default=1_048_576, ge=1024)  # CSV imports up to 1 MB

    RATE_LIMIT_STORAGE_URI: SecretStr = SecretStr("memory://")
    LOGIN_RATE_LIMIT: str = "5/minute"
    REGISTER_RATE_LIMIT: str = "5/hour"
    PASSWORD_RESET_RATE_LIMIT: str = "3/hour"  # noqa: S105 - a rate, not a secret
    API_RATE_LIMIT: str = "120/minute"
    ASSISTANT_RATE_LIMIT: str = "20/hour"

    # Large-language-model provider for the assistant's final answer.
    # "none" keeps everything local: agents still compute every figure and a
    # deterministic template writes the summary.
    LLM_PROVIDER: Literal["none", "anthropic"] = "none"
    ANTHROPIC_API_KEY: SecretStr | None = None
    LLM_MODEL: str = "claude-sonnet-5-5"
    LLM_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0, le=120)

    # Where password-reset links point. Delivery: "log" (development) or "smtp".
    FRONTEND_URL: str = "http://localhost:3000"
    EMAIL_BACKEND: Literal["log", "smtp"] = "log"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_FROM: str = "no-reply@localhost"

    @field_validator("CORS_ORIGINS", "ALLOWED_HOSTS", mode="before")
    @classmethod
    def _split_lists(cls, value: object) -> object:
        return _split(value)

    @field_validator("CORS_ORIGINS")
    @classmethod
    def _no_wildcard(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("CORS_ORIGINS must list explicit origins, not '*'")
        return value

    @field_validator("ANTHROPIC_API_KEY", mode="before")
    @classmethod
    def _empty_key_is_none(cls, value: object) -> object:
        return None if value in ("", None) else value

    @field_validator("SECRET_KEY")
    @classmethod
    def _strong_secret(cls, value: SecretStr) -> SecretStr:
        raw = value.get_secret_value()
        if len(raw) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        if any(marker in raw.lower() for marker in _WEAK_MARKERS):
            raise ValueError("SECRET_KEY looks like a placeholder; generate a random value")
        return value

    @field_validator("DATABASE_URL")
    @classmethod
    def _psycopg3_driver(cls, value: SecretStr) -> SecretStr:
        # Older .env files use postgresql:// (psycopg2). The project ships the
        # psycopg 3 driver only, so point SQLAlchemy at it explicitly.
        url = value.get_secret_value()
        for prefix in ("postgresql://", "postgres://", "postgresql+psycopg2://"):
            if url.startswith(prefix):
                return SecretStr("postgresql+psycopg://" + url[len(prefix) :])
        return value

    @property
    def llm_enabled(self) -> bool:
        return self.LLM_PROVIDER == "anthropic" and self.ANTHROPIC_API_KEY is not None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
