"""Typed environment-backed application configuration."""

from enum import StrEnum
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    """Supported OpsMind runtime environments."""

    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated application settings loaded from ``OPSMIND_`` variables."""

    model_config = SettingsConfigDict(env_prefix="OPSMIND_")

    application_name: str = "OpsMind"
    service_name: str = "opsmind-api"
    environment: Environment = Environment.LOCAL
    debug: bool = False
    api_v1_prefix: str = "/api/v1"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear cached settings for explicit test isolation."""
    get_settings.cache_clear()
