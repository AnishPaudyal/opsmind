"""Tests for the process-health and application-readiness API."""

import json
import logging

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from opsmind.api.dependencies import get_readiness_probe
from opsmind.api.routes.health import BUILD_REVISION_HEADER
from opsmind.application import create_app
from opsmind.core.config import Environment, PersistenceBackend, Settings
from opsmind.observability import HTTP_LOGGER_NAME, REQUEST_ID_HEADER
from opsmind.readiness import (
    PersistenceCheckStatus,
    ReadinessResult,
    ReadinessStatus,
)


class StaticReadinessProbe:
    """Return one deterministic readiness result for route tests."""

    def __init__(self, result: ReadinessResult) -> None:
        self.result = result

    def check_readiness(self) -> ReadinessResult:
        return self.result


def create_test_client() -> TestClient:
    """Create a client with deterministic test settings."""
    settings = Settings(
        application_name="OpsMind Test",
        service_name="opsmind-test-api",
        environment=Environment.TEST,
        debug=False,
        api_v1_prefix="/api/v1",
    )
    return TestClient(create_app(settings))


def test_health_returns_exact_public_contract() -> None:
    response = create_test_client().get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {
        "status": "ok",
        "service": "opsmind-test-api",
        "environment": "test",
    }
    assert BUILD_REVISION_HEADER not in response.headers


def test_health_exposes_configured_release_revision_without_changing_body() -> None:
    revision = "a" * 40
    settings = Settings(
        service_name="opsmind-test-api",
        environment=Environment.TEST,
        build_revision=revision,
    )

    response = TestClient(create_app(settings)).get("/health")

    assert response.status_code == 200
    assert response.headers[BUILD_REVISION_HEADER] == revision
    assert response.json() == {
        "status": "ok",
        "service": "opsmind-test-api",
        "environment": "test",
    }


def test_memory_readiness_returns_bounded_200_and_one_observability_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = create_test_client()
    messages: list[str] = []
    monkeypatch.setattr(
        logging.getLogger(HTTP_LOGGER_NAME),
        "info",
        lambda message: messages.append(str(message)),
    )

    response = client.get("/ready", headers={REQUEST_ID_HEADER: "ready-123"})

    assert response.status_code == 200
    assert response.headers.get_list(REQUEST_ID_HEADER) == ["ready-123"]
    assert response.json() == {
        "status": "ready",
        "service": "opsmind-test-api",
        "environment": "test",
        "backend": "memory",
        "checks": {"persistence": "ready"},
    }
    assert len(messages) == 1
    event = json.loads(messages[0])
    assert event["route"] == "/ready"
    assert event["status_code"] == 200
    assert event["error_category"] == "none"


def test_readiness_dependency_override_returns_bounded_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        service_name="opsmind-test-api",
        environment=Environment.TEST,
    )
    application = create_app(settings)
    application.dependency_overrides[get_readiness_probe] = lambda: (
        StaticReadinessProbe(
            ReadinessResult(
                status=ReadinessStatus.NOT_READY,
                backend=PersistenceBackend.MEMORY,
                persistence=PersistenceCheckStatus.NOT_READY,
            )
        )
    )
    messages: list[str] = []
    monkeypatch.setattr(
        logging.getLogger(HTTP_LOGGER_NAME),
        "info",
        lambda message: messages.append(str(message)),
    )

    response = TestClient(application).get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready",
        "service": "opsmind-test-api",
        "environment": "test",
        "backend": "memory",
        "checks": {"persistence": "not_ready"},
    }
    assert len(response.headers.get_list(REQUEST_ID_HEADER)) == 1
    assert len(messages) == 1
    event = json.loads(messages[0])
    assert event["route"] == "/ready"
    assert event["status_code"] == 503
    assert event["error_category"] == "dependency_unavailable"


def test_unavailable_postgresql_is_lazy_safe_and_does_not_change_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "synthetic-password"
    settings = Settings(
        service_name="opsmind-postgresql-test",
        environment=Environment.TEST,
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(
            f"postgresql+psycopg://opsmind:{secret}@127.0.0.1:1/opsmind_test"
        ),
    )
    application = create_app(settings)
    messages: list[str] = []
    monkeypatch.setattr(
        logging.getLogger(HTTP_LOGGER_NAME),
        "info",
        lambda message: messages.append(str(message)),
    )

    with TestClient(application) as client:
        health = client.get("/health")
        readiness = client.get("/ready")

    assert health.status_code == 200
    assert health.json() == {
        "status": "ok",
        "service": "opsmind-postgresql-test",
        "environment": "test",
    }
    assert readiness.status_code == 503
    assert readiness.json() == {
        "status": "not_ready",
        "service": "opsmind-postgresql-test",
        "environment": "test",
        "backend": "postgresql",
        "checks": {"persistence": "not_ready"},
    }
    assert len(messages) == 2
    ready_event = json.loads(messages[1])
    assert ready_event["route"] == "/ready"
    assert ready_event["error_category"] == "dependency_unavailable"
    combined_public_output = readiness.text + messages[1]
    for excluded in (
        secret,
        "127.0.0.1",
        "127.0.0.1:1",
        "postgresql+psycopg",
        "SELECT version_num",
        "alembic_version",
        "Traceback",
    ):
        assert excluded not in combined_public_output


def test_health_openapi_contract_is_documented() -> None:
    response = create_test_client().get("/openapi.json")
    schema = response.json()
    operation = schema["paths"]["/health"]["get"]
    health_schema = schema["components"]["schemas"]["HealthResponse"]

    assert response.status_code == 200
    assert operation["summary"] == "Check process health"
    assert operation["description"] == (
        "Report deterministic health for the running API process."
    )
    assert operation["tags"] == ["health"]
    assert "200" in operation["responses"]
    assert operation["responses"]["200"]["headers"][BUILD_REVISION_HEADER] == {
        "description": (
            "Full Git revision of the running release when build identity is available."
        ),
        "schema": {
            "type": "string",
            "pattern": "^[0-9a-f]{40}$",
        },
    }
    assert health_schema["required"] == ["status", "service", "environment"]
    assert health_schema["properties"]["status"]["const"] == "ok"


def test_readiness_openapi_contract_is_unversioned_and_bounded() -> None:
    schema = create_test_client().get("/openapi.json").json()
    operation = schema["paths"]["/ready"]["get"]
    readiness_schema = schema["components"]["schemas"]["ReadinessResponse"]
    checks_schema = schema["components"]["schemas"]["ReadinessChecks"]

    assert operation["summary"] == "Check application readiness"
    assert operation["tags"] == ["health"]
    assert set(operation["responses"]) == {"200", "503"}
    for response_code in ("200", "503"):
        assert operation["responses"][response_code]["content"]["application/json"][
            "schema"
        ] == {"$ref": "#/components/schemas/ReadinessResponse"}
    assert readiness_schema["required"] == [
        "status",
        "service",
        "environment",
        "backend",
        "checks",
    ]
    assert checks_schema["required"] == ["persistence"]
    assert schema["components"]["schemas"]["ReadinessStatus"]["enum"] == [
        "ready",
        "not_ready",
    ]
    assert schema["components"]["schemas"]["PersistenceCheckStatus"]["enum"] == [
        "ready",
        "not_ready",
    ]
    assert "/api/v1/ready" not in schema["paths"]


def test_api_v1_prefix_does_not_expose_an_empty_business_endpoint() -> None:
    client = create_test_client()

    assert client.get("/api/v1").status_code == 404
    assert client.get("/api/v1/").status_code == 404
