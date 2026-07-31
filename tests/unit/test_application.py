"""Tests for FastAPI application construction."""

import os
from importlib import import_module
from typing import Protocol, cast

import pytest
from fastapi import FastAPI

from opsmind.application import create_app
from opsmind.core.config import (
    Environment,
    Settings,
    get_settings,
    reset_settings_cache,
)


class ApplicationModule(Protocol):
    """Typed view of the ASGI entry-point module."""

    app: FastAPI


def test_create_app_uses_supplied_settings_for_metadata() -> None:
    settings = Settings(
        application_name="OpsMind Test",
        service_name="opsmind-test-api",
        environment=Environment.TEST,
        debug=True,
        api_v1_prefix="/api/v1",
    )

    application = create_app(settings)

    assert isinstance(application, FastAPI)
    assert application.title == "OpsMind Test"
    assert application.description == "opsmind-test-api API"
    assert application.debug is True


def test_create_app_provides_the_same_settings_instance() -> None:
    settings = Settings(environment=Environment.TEST)
    application = create_app(settings)

    settings_provider = application.dependency_overrides[get_settings]

    assert settings_provider() is settings


def test_root_router_has_only_the_unversioned_health_business_route() -> None:
    settings = Settings(environment=Environment.TEST, api_v1_prefix="/api/v1")
    application = create_app(settings)
    route_paths = set(cast(dict[str, object], application.openapi()["paths"]))

    assert "/health" in route_paths
    assert settings.api_v1_prefix not in route_paths
    assert not any(
        path.startswith(f"{settings.api_v1_prefix}/") for path in route_paths
    )


def test_main_exposes_the_default_asgi_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable_name in tuple(os.environ):
        if variable_name.startswith("OPSMIND_"):
            monkeypatch.delenv(variable_name, raising=False)
    reset_settings_cache()

    main_module = cast(ApplicationModule, import_module("opsmind.main"))

    assert isinstance(main_module.app, FastAPI)
    assert main_module.app.title == "OpsMind"

    reset_settings_cache()
