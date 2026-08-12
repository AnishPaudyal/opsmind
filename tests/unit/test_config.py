"""Tests for typed OpsMind settings."""

import os

import pytest
from pydantic import SecretStr, ValidationError

from opsmind.core.config import (
    Environment,
    PersistenceBackend,
    Settings,
    get_settings,
    reset_settings_cache,
)


def clear_opsmind_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove ambient OpsMind variables for deterministic default tests."""
    for variable_name in tuple(os.environ):
        if variable_name.startswith("OPSMIND_"):
            monkeypatch.delenv(variable_name, raising=False)


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_opsmind_environment(monkeypatch)

    settings = Settings()

    assert settings.application_name == "OpsMind"
    assert settings.service_name == "opsmind-api"
    assert settings.environment is Environment.LOCAL
    assert settings.debug is False
    assert settings.api_v1_prefix == "/api/v1"
    assert settings.persistence_backend is PersistenceBackend.MEMORY
    assert settings.database_url is None
    assert settings.auth_issuer is None
    assert settings.auth_audience is None
    assert settings.auth_public_key is None
    assert settings.auth_jwks_url is None
    assert settings.auth_algorithm == "RS256"
    assert settings.auth_clock_leeway_seconds == 0
    assert settings.auth_jwks_timeout_seconds == 5.0
    assert settings.auth_jwks_cache_seconds == 300.0
    assert settings.authentication_configured is False
    assert settings.static_authentication_configured is False
    assert settings.jwks_authentication_configured is False


def test_settings_accept_prefixed_environment_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_opsmind_environment(monkeypatch)
    monkeypatch.setenv("OPSMIND_APPLICATION_NAME", "OpsMind Override")
    monkeypatch.setenv("OPSMIND_SERVICE_NAME", "override-api")
    monkeypatch.setenv("OPSMIND_ENVIRONMENT", "staging")
    monkeypatch.setenv("OPSMIND_DEBUG", "true")
    monkeypatch.setenv("OPSMIND_API_V1_PREFIX", "/custom/v1")

    settings = Settings()

    assert settings.application_name == "OpsMind Override"
    assert settings.service_name == "override-api"
    assert settings.environment is Environment.STAGING
    assert settings.debug is True
    assert settings.api_v1_prefix == "/custom/v1"


def test_settings_accept_complete_authentication_configuration() -> None:
    public_key = "synthetic-public-verification-key"
    settings = Settings(
        auth_issuer="https://identity.example.test/",
        auth_audience="opsmind-api",
        auth_public_key=SecretStr(public_key),
        auth_clock_leeway_seconds=5,
    )

    assert settings.authentication_configured is True
    assert settings.static_authentication_configured is True
    assert settings.jwks_authentication_configured is False
    assert settings.auth_algorithm == "RS256"
    assert settings.auth_clock_leeway_seconds == 5
    assert public_key not in repr(settings)
    assert public_key not in str(settings.model_dump())


@pytest.mark.parametrize(
    "values",
    [
        {"auth_issuer": "https://identity.example.test/"},
        {"auth_audience": "opsmind-api"},
        {"auth_public_key": SecretStr("synthetic-public-key")},
        {
            "auth_issuer": "https://identity.example.test/",
            "auth_audience": "opsmind-api",
        },
    ],
)
def test_settings_reject_partial_authentication_configuration(
    values: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="must be configured together"):
        Settings(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("auth_issuer", ""),
        ("auth_issuer", " padded "),
        ("auth_audience", ""),
        ("auth_audience", " padded "),
        ("auth_public_key", SecretStr("   ")),
        ("auth_algorithm", "HS256"),
        ("auth_clock_leeway_seconds", -1),
        ("auth_clock_leeway_seconds", 61),
    ],
)
def test_settings_reject_invalid_authentication_configuration(
    field: str,
    value: object,
) -> None:
    complete: dict[str, object] = {
        "auth_issuer": "https://identity.example.test/",
        "auth_audience": "opsmind-api",
        "auth_public_key": SecretStr("synthetic-public-key"),
    }
    complete[field] = value

    with pytest.raises(ValidationError):
        Settings(**complete)  # type: ignore[arg-type]


def test_settings_reject_an_invalid_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_opsmind_environment(monkeypatch)
    monkeypatch.setenv("OPSMIND_ENVIRONMENT", "preview")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_reject_an_invalid_boolean(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_opsmind_environment(monkeypatch)
    monkeypatch.setenv("OPSMIND_DEBUG", "not-a-boolean")

    with pytest.raises(ValidationError):
        Settings()


def test_settings_cache_is_stable_and_explicitly_resettable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_opsmind_environment(monkeypatch)
    reset_settings_cache()


def test_settings_accept_explicit_memory_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clear_opsmind_environment(monkeypatch)
    monkeypatch.setenv("OPSMIND_PERSISTENCE_BACKEND", "memory")

    settings = Settings()

    assert settings.persistence_backend is PersistenceBackend.MEMORY
    assert settings.database_url is None


def test_settings_accept_postgresql_with_selected_driver_url() -> None:
    settings = Settings(
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(
            "postgresql+psycopg://user:password@localhost:5432/opsmind"
        ),
    )

    assert settings.persistence_backend is PersistenceBackend.POSTGRESQL
    assert settings.database_url is not None


def test_settings_require_database_url_for_postgresql() -> None:
    with pytest.raises(
        ValidationError,
        match="OPSMIND_DATABASE_URL is required when PostgreSQL is selected",
    ):
        Settings(persistence_backend=PersistenceBackend.POSTGRESQL)


def test_settings_reject_invalid_persistence_backend() -> None:
    with pytest.raises(ValidationError):
        Settings(persistence_backend="sqlite")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql://user:password@localhost/opsmind",
        "postgresql+asyncpg://user:password@localhost/opsmind",
        "sqlite:///opsmind.db",
        "not-a-url",
    ],
)
def test_settings_require_psycopg_sqlalchemy_url(database_url: str) -> None:
    with pytest.raises(ValidationError) as error:
        Settings(
            persistence_backend=PersistenceBackend.POSTGRESQL,
            database_url=SecretStr(database_url),
        )

    assert database_url not in str(error.value)


def test_settings_hide_database_credentials_in_representations() -> None:
    password = "do-not-display-this-password"
    settings = Settings(
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(
            f"postgresql+psycopg://user:{password}@localhost/opsmind"
        ),
    )

    assert password not in repr(settings)
    assert password not in str(settings.model_dump())

    first_settings = get_settings()
    second_settings = get_settings()
    reset_settings_cache()
    third_settings = get_settings()

    assert second_settings is first_settings
    assert third_settings is not first_settings

    reset_settings_cache()


def test_settings_accept_complete_jwks_authentication_configuration() -> None:
    settings = Settings(
        auth_issuer="https://identity.example.test/",
        auth_audience="opsmind-project-123",
        auth_jwks_url="https://identity.example.test/oauth/v2/keys",
        auth_jwks_timeout_seconds=4.0,
        auth_jwks_cache_seconds=240.0,
    )

    assert settings.authentication_configured is True
    assert settings.static_authentication_configured is False
    assert settings.jwks_authentication_configured is True
    assert settings.auth_jwks_timeout_seconds == 4.0
    assert settings.auth_jwks_cache_seconds == 240.0


def test_settings_reject_static_key_and_jwks_together() -> None:
    with pytest.raises(ValidationError, match="exactly one"):
        Settings(
            auth_issuer="https://identity.example.test/",
            auth_audience="opsmind-project-123",
            auth_public_key=SecretStr("synthetic-public-key"),
            auth_jwks_url="https://identity.example.test/oauth/v2/keys",
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("auth_jwks_url", ""),
        ("auth_jwks_url", " padded "),
        ("auth_jwks_timeout_seconds", 0),
        ("auth_jwks_timeout_seconds", 11),
        ("auth_jwks_cache_seconds", 0),
        ("auth_jwks_cache_seconds", 3601),
    ],
)
def test_settings_reject_invalid_jwks_configuration_values(
    field: str,
    value: object,
) -> None:
    complete: dict[str, object] = {
        "auth_issuer": "https://identity.example.test/",
        "auth_audience": "opsmind-project-123",
        "auth_jwks_url": "https://identity.example.test/oauth/v2/keys",
    }
    complete[field] = value

    with pytest.raises(ValidationError):
        Settings(**complete)  # type: ignore[arg-type]
