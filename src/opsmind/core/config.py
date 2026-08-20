"""Typed environment-backed application configuration."""

import re
from enum import StrEnum
from functools import lru_cache
from ipaddress import ip_address
from urllib.parse import urlsplit

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
    build_revision: str | None = None
    auth_issuer: str | None = None
    auth_audience: str | None = None
    auth_public_key: SecretStr | None = None
    auth_jwks_url: str | None = None
    auth_algorithm: str = "RS256"
    auth_clock_leeway_seconds: int = Field(default=0, ge=0, le=60)
    auth_jwks_timeout_seconds: float = Field(default=5.0, gt=0, le=10)
    auth_jwks_cache_seconds: float = Field(default=300.0, gt=0, le=3600)
    cors_allowed_origins: tuple[str, ...] = ()

    @field_validator("cors_allowed_origins")
    @classmethod
    def validate_cors_allowed_origins(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Normalize unique exact origins and permit HTTP only on loopback."""
        normalized_origins: list[str] = []
        for origin in value:
            if not origin or origin != origin.strip() or "*" in origin:
                raise ValueError(
                    "OPSMIND_CORS_ALLOWED_ORIGINS must contain exact origins"
                )
            parsed = urlsplit(origin)
            try:
                port = parsed.port
            except ValueError:
                raise ValueError(
                    "OPSMIND_CORS_ALLOWED_ORIGINS must contain exact origins"
                ) from None
            if (
                parsed.scheme not in {"http", "https"}
                or parsed.hostname is None
                or parsed.username is not None
                or parsed.password is not None
                or parsed.path != ""
                or parsed.query != ""
                or parsed.fragment != ""
                or parsed.netloc.endswith(":")
                or any(character.isspace() for character in parsed.hostname)
            ):
                raise ValueError(
                    "OPSMIND_CORS_ALLOWED_ORIGINS must contain exact origins"
                )

            hostname = parsed.hostname.lower()
            try:
                normalized_hostname = (
                    hostname
                    if ":" in hostname
                    else hostname.encode("idna").decode("ascii")
                )
            except UnicodeError:
                raise ValueError(
                    "OPSMIND_CORS_ALLOWED_ORIGINS must contain exact origins"
                ) from None
            if parsed.scheme == "http":
                try:
                    loopback = ip_address(normalized_hostname).is_loopback
                except ValueError:
                    loopback = normalized_hostname == "localhost"
                if not loopback:
                    raise ValueError(
                        "OPSMIND_CORS_ALLOWED_ORIGINS permits HTTP only for "
                        "loopback development origins"
                    )

            canonical_host = (
                f"[{normalized_hostname}]"
                if ":" in normalized_hostname
                else normalized_hostname
            )
            default_port = (parsed.scheme == "http" and port == 80) or (
                parsed.scheme == "https" and port == 443
            )
            port_suffix = "" if port is None or default_port else f":{port}"
            normalized_origins.append(
                f"{parsed.scheme}://{canonical_host}{port_suffix}"
            )

        if len(set(normalized_origins)) != len(normalized_origins):
            raise ValueError("OPSMIND_CORS_ALLOWED_ORIGINS must not contain duplicates")
        return tuple(normalized_origins)

    @field_validator("build_revision")
    @classmethod
    def validate_build_revision(cls, value: str | None) -> str | None:
        """Require an exact lowercase full Git SHA when build identity is set."""
        if value is not None and re.fullmatch(r"[0-9a-f]{40}", value) is None:
            raise ValueError(
                "OPSMIND_BUILD_REVISION must be a 40-character lowercase Git SHA"
            )
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: SecretStr | None) -> SecretStr | None:
        """Require the selected synchronous Psycopg SQLAlchemy URL form."""
        if value is not None:
            parse_postgresql_database_url(value)
        return value

    @field_validator("auth_issuer", "auth_audience", "auth_jwks_url")
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
        """Require one complete JWT trust source while allowing deny-all."""
        static_key_configured = self.auth_public_key is not None
        jwks_configured = self.auth_jwks_url is not None
        any_authentication_value = any(
            (
                self.auth_issuer is not None,
                self.auth_audience is not None,
                static_key_configured,
                jwks_configured,
            )
        )
        if not any_authentication_value:
            return self

        if (
            self.auth_issuer is None
            or self.auth_audience is None
            or static_key_configured == jwks_configured
        ):
            raise ValueError(
                "OPSMIND_AUTH_ISSUER and OPSMIND_AUTH_AUDIENCE must be "
                "configured together with exactly one of "
                "OPSMIND_AUTH_PUBLIC_KEY or OPSMIND_AUTH_JWKS_URL"
            )
        return self

    @property
    def authentication_configured(self) -> bool:
        """Return whether one complete JWT trust boundary is configured."""
        return self.auth_issuer is not None

    @property
    def static_authentication_configured(self) -> bool:
        """Return whether authentication uses one configured static RSA key."""
        return self.auth_public_key is not None

    @property
    def jwks_authentication_configured(self) -> bool:
        """Return whether authentication uses a configured JWKS endpoint."""
        return self.auth_jwks_url is not None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""
    return Settings()


def reset_settings_cache() -> None:
    """Clear cached settings for explicit test isolation."""
    get_settings.cache_clear()
