"""Tests for the process-health API."""

from fastapi.testclient import TestClient

from opsmind.application import create_app
from opsmind.core.config import Environment, Settings


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
    assert health_schema["required"] == ["status", "service", "environment"]
    assert health_schema["properties"]["status"]["const"] == "ok"


def test_api_v1_prefix_does_not_expose_an_empty_business_endpoint() -> None:
    client = create_test_client()

    assert client.get("/api/v1").status_code == 404
    assert client.get("/api/v1/").status_code == 404
