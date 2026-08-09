"""Typed environment-backed application configuration."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
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
    auth_issuer: str | None = None
    auth_audience: str | None = None
    auth_public_key: SecretStr | None = None
    auth_algorithm: str = "RS256"
    auth_clock_leeway_seconds: int = Field(default=0, ge=0, le=60)

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        """Require the selected synchronous Psycopg SQLAlchemy URL form."""
        if value is not None:
            parse_postgresql_database_url(value)
        return value

    @field_validator("auth_issuer", "auth_audience")
    @classmethod
    def validate_authentication_text(cls, value: str | None) -> str | None:
        """Reject blank or ambiguously padded authentication identifiers."""
        if value is not None and (not value or value != value.strip()):
            raise ValueError("authentication identifiers must be non-empty and trimmed")
        return value

    @field_validator("auth_public_key")
    @classmethod
    def validate_authentication_key(
        cls,
        value: SecretStr | None,
    ) -> SecretStr | None:
        """Reject an explicitly blank public verification key."""
        if value is not None and not value.get_secret_value().strip():
            raise ValueError("authentication public key must not be empty")
        return value

    @field_validator("auth_algorithm")
    @classmethod
    def validate_authentication_algorithm(cls, value: str) -> str:
        """Enforce the initial explicit asymmetric algorithm allowlist."""
        if value != "RS256":
            raise ValueError("OPSMIND_AUTH_ALGORITHM must be RS256")
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

    @model_validator(mode="after")
    def require_complete_authentication_configuration(self) -> "Settings":
        """Reject partially configured token validation while allowing deny-all."""
        configured = (
            self.auth_issuer is not None,
            self.auth_audience is not None,
            self.auth_public_key is not None,
        )
        if any(configured) and not all(configured):
            raise ValueError(
                "OPSMIND_AUTH_ISSUER, OPSMIND_AUTH_AUDIENCE, and "
                "OPSMIND_AUTH_PUBLIC_KEY must be configured together"
            )
        return self

    @property
    def authentication_configured(self) -> bool:
        """Return whether the complete JWT trust boundary is configured."""
        return self.auth_issuer is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear cached settings for explicit test isolation."""
    get_settings.cache_clear()
