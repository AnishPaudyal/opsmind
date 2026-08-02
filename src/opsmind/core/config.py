"""Typed environment-backed application configuration."""

from enum import StrEnum
from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ArgumentError


class Environment(StrEnum):
    """Supported OpsMind runtime environments."""

    LOCAL = "local"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class PersistenceBackend(StrEnum):
    """Supported operational-data persistence backends."""

    MEMORY = "memory"
    POSTGRESQL = "postgresql"


def parse_postgresql_database_url(database_url: SecretStr | str | URL) -> URL:
    """Parse the selected Psycopg SQLAlchemy URL without exposing its secret."""
    if isinstance(database_url, URL):
        parsed_url = database_url
    else:
        raw_url = (
            database_url.get_secret_value()
            if isinstance(database_url, SecretStr)
            else database_url
        )
        try:
            parsed_url = make_url(raw_url)
        except ArgumentError:
            raise ValueError(
                "database URL must be a valid postgresql+psycopg URL"
            ) from None
    if parsed_url.drivername != "postgresql+psycopg" or not parsed_url.database:
        raise ValueError("database URL must be a valid postgresql+psycopg URL")
    return parsed_url


class Settings(BaseSettings):
    """Validated application settings loaded from ``OPSMIND_`` variables."""

    model_config = SettingsConfigDict(env_prefix="OPSMIND_")

    application_name: str = "OpsMind"
    service_name: str = "opsmind-api"
    environment: Environment = Environment.LOCAL
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    persistence_backend: PersistenceBackend = PersistenceBackend.MEMORY
    database_url: SecretStr | None = None

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        """Require the selected synchronous Psycopg SQLAlchemy URL form."""
        if value is not None:
            parse_postgresql_database_url(value)
        return value

    @model_validator(mode="after")
    def require_postgresql_database_url(self) -> "Settings":
        """Reject an explicit PostgreSQL backend without connection settings."""
        if (
            self.persistence_backend is PersistenceBackend.POSTGRESQL
            and self.database_url is None
        ):
            raise ValueError(
                "OPSMIND_DATABASE_URL is required when PostgreSQL is selected"
            )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear cached settings for explicit test isolation."""
    get_settings.cache_clear()
