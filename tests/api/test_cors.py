"""Exact-origin CORS integration tests."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from opsmind.application import create_app
from opsmind.core.config import Environment, Settings
from tests.security import authenticated_test_client, create_authenticated_test_app

ALLOWED_ORIGIN = "http://localhost:5173"
SECOND_ALLOWED_ORIGIN = "https://frontend.example.test"
DISALLOWED_ORIGIN = "https://attacker.example.test"


def make_app(*origins: str) -> FastAPI:
    """Create one deterministic application with explicit CORS origins."""
    return create_authenticated_test_app(
        Settings(
            environment=Environment.TEST,
            build_revision="a" * 40,
            cors_allowed_origins=origins,
        )
    )


def test_no_cors_setting_emits_no_cross_origin_headers() -> None:
    response = TestClient(create_app(Settings(environment=Environment.TEST))).get(
        "/health",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_one_and_multiple_exact_origins_are_allowed_without_credentials() -> None:
    client = TestClient(make_app(ALLOWED_ORIGIN, SECOND_ALLOWED_ORIGIN))

    for origin in (ALLOWED_ORIGIN, SECOND_ALLOWED_ORIGIN):
        response = client.get("/health", headers={"Origin": origin})
        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert "access-control-allow-credentials" not in response.headers
        exposed = response.headers["access-control-expose-headers"].lower()
        assert "x-request-id" in exposed
        assert "x-opsmind-revision" in exposed
        assert response.headers["x-request-id"]
        assert response.headers["x-opsmind-revision"] == "a" * 40


def test_allowed_authorization_preflight_is_explicit_and_bounded() -> None:
    response = TestClient(make_app(ALLOWED_ORIGIN)).options(
        "/api/v1/products",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": (
                "Authorization, Content-Type, X-Request-ID"
            ),
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert response.headers["access-control-max-age"] == "600"
    methods = {
        value.strip()
        for value in response.headers["access-control-allow-methods"].split(",")
    }
    assert methods == {"GET", "POST", "PUT", "OPTIONS"}
    headers = {
        value.strip().lower()
        for value in response.headers["access-control-allow-headers"].split(",")
    }
    assert {"authorization", "content-type", "x-request-id"} <= headers
    assert "access-control-allow-credentials" not in response.headers


def test_disallowed_origin_is_not_reflected_for_actual_or_preflight_requests() -> None:
    client = TestClient(make_app(ALLOWED_ORIGIN))
    actual = client.get("/health", headers={"Origin": DISALLOWED_ORIGIN})
    preflight = client.options(
        "/api/v1/products",
        headers={
            "Origin": DISALLOWED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization",
        },
    )

    assert actual.status_code == 200
    assert "access-control-allow-origin" not in actual.headers
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers


def test_cors_never_weakens_route_authentication() -> None:
    response = TestClient(make_app(ALLOWED_ORIGIN)).get(
        "/api/v1/products",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_authenticated_cross_origin_read_keeps_exact_origin_and_no_cookies() -> None:
    response = authenticated_test_client(make_app(ALLOWED_ORIGIN)).get(
        "/api/v1/products",
        headers={"Origin": ALLOWED_ORIGIN},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
    assert "access-control-allow-credentials" not in response.headers
