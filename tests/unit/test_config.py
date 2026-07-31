"""Tests for typed OpsMind settings."""

import os

import pytest
from pydantic import ValidationError

from opsmind.core.config import (
    Environment,
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

    first_settings = get_settings()
    second_settings = get_settings()
    reset_settings_cache()
    third_settings = get_settings()

    assert second_settings is first_settings
    assert third_settings is not first_settings

    reset_settings_cache()
