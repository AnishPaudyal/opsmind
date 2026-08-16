"""API security-boundary, authorization, and attribution tests."""

import json
import logging
from datetime import UTC, date, datetime, timedelta
from typing import cast

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm
from pydantic import SecretStr

from opsmind.api.dependencies import get_authenticator
from opsmind.application import create_app
from opsmind.core.config import Environment, Settings
from opsmind.observability import HTTP_LOGGER_NAME, REQUEST_ID_HEADER
from opsmind.repositories.memory import InMemoryProductInventoryRepository
from opsmind.security import AuthenticationError, Permission
from tests.security import (
    TEST_BEARER_TOKEN,
    authenticated_test_client,
    create_authenticated_test_app,
)
from tests.security import (
    test_principal as make_test_principal,
)


def settings() -> Settings:
    """Return deterministic test settings."""
    return Settings(environment=Environment.TEST)


def client_with_permissions(*permissions: Permission) -> TestClient:
    """Return a client authenticated with exactly the requested permissions."""
    application = create_authenticated_test_app(
        settings(),
        principal=make_test_principal(permissions=frozenset(permissions)),
    )
    return authenticated_test_client(application)


def product_payload() -> dict[str, object]:
    return {
        "sku": "SECURITY-001",
        "name": "Security test product",
        "unit_of_measure": "each",
        "lead_time_days": 2,
    }


def create_actionable_review(client: TestClient) -> str:
    """Create one stored actionable recommendation through authorized routes."""
    product_response = client.post("/api/v1/products", json=product_payload())
    assert product_response.status_code == 201
    product_id = cast(str, product_response.json()["id"])
    assert (
        client.put(
            f"/api/v1/products/{product_id}/inventory",
            json={"on_hand_quantity": 0, "allocated_quantity": 0},
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/v1/products/{product_id}/demand",
            json={
                "observations": [
                    {"demand_date": date(2026, 8, day).isoformat(), "quantity": 5}
                    for day in range(1, 4)
                ]
            },
        ).status_code
        == 201
    )
    review_response = client.post(
        f"/api/v1/products/{product_id}/reorder-recommendations"
    )
    assert review_response.status_code == 201
    return cast(str, review_response.json()["recommendation_id"])


@pytest.mark.parametrize(
    "path", ["/health", "/ready", "/openapi.json", "/docs", "/redoc"]
)
def test_operational_and_api_description_endpoints_are_public(path: str) -> None:
    response = TestClient(create_app(settings())).get(path)

    assert response.status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Basic opaque-value"},
        {"Authorization": "Bearer invalid-token"},
    ],
)
def test_protected_endpoint_returns_bounded_401(headers: dict[str, str]) -> None:
    response = TestClient(create_app(settings())).get(
        "/api/v1/products",
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers[REQUEST_ID_HEADER]
    assert "invalid-token" not in response.text


def test_duplicate_authorization_headers_fail_closed() -> None:
    application = create_authenticated_test_app(settings())
    response = TestClient(application).get(
        "/api/v1/products",
        headers=[
            ("Authorization", f"Bearer {TEST_BEARER_TOKEN}"),
            ("Authorization", "Bearer attacker-token"),
        ],
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_missing_permission_returns_403_before_repository_mutation() -> None:
    repository = InMemoryProductInventoryRepository()
    application = create_authenticated_test_app(
        settings(),
        product_inventory_repository=repository,
        principal=make_test_principal(
            permissions=frozenset({Permission.BUSINESS_READ})
        ),
    )
    client = authenticated_test_client(application)

    response = client.post("/api/v1/products", json=product_payload())

    assert response.status_code == 403
    assert response.json() == {"detail": "Insufficient permission."}
    assert "WWW-Authenticate" not in response.headers
    assert repository.list_products() == ()


def test_permissions_are_independent_for_reads_writes_and_decisions() -> None:
    read_client = client_with_permissions(Permission.BUSINESS_READ)
    write_client = client_with_permissions(Permission.BUSINESS_WRITE)
    decide_client = client_with_permissions(Permission.RECOMMENDATION_DECIDE)

    assert read_client.get("/api/v1/products").status_code == 200
    assert (
        read_client.post("/api/v1/products", json=product_payload()).status_code == 403
    )
    assert (
        write_client.post("/api/v1/products", json=product_payload()).status_code == 201
    )
    assert write_client.get("/api/v1/products").status_code == 403
    assert decide_client.get("/api/v1/products").status_code == 403
    decision_path = (
        "/api/v1/reorder-recommendations/00000000-0000-0000-0000-000000000099/approve"
    )
    assert read_client.post(decision_path, json={}).status_code == 403
    assert write_client.post(decision_path, json={}).status_code == 403
    assert decide_client.post(decision_path, json={}).status_code == 404


def test_injected_authenticators_are_isolated_per_application() -> None:
    first = create_authenticated_test_app(
        settings(),
        principal=make_test_principal(principal_id="first-reviewer"),
        token="first-token",
    )
    second = create_authenticated_test_app(
        settings(),
        principal=make_test_principal(principal_id="second-reviewer"),
        token="second-token",
    )
    first_authenticator = first.dependency_overrides[get_authenticator]()
    second_authenticator = second.dependency_overrides[get_authenticator]()

    assert first_authenticator is not second_authenticator
    assert first_authenticator.authenticate("first-token").principal_id == (
        "first-reviewer"
    )
    assert second_authenticator.authenticate("second-token").principal_id == (
        "second-reviewer"
    )
    with pytest.raises(AuthenticationError):
        first_authenticator.authenticate("second-token")


def test_trusted_principal_controls_decision_and_audit_attribution() -> None:
    application = create_authenticated_test_app(
        settings(),
        principal=make_test_principal(principal_id="trusted-reviewer-7"),
    )
    client = authenticated_test_client(application)
    recommendation_id = create_actionable_review(client)

    spoof_response = client.post(
        f"/api/v1/reorder-recommendations/{recommendation_id}/approve",
        json={"decided_by": "spoofed-actor", "approved_quantity": 10},
    )
    pending_response = client.get(
        f"/api/v1/reorder-recommendations/{recommendation_id}"
    )
    approval_response = client.post(
        f"/api/v1/reorder-recommendations/{recommendation_id}/approve",
        json={"approved_quantity": 10, "note": "Authorized decision."},
    )
    audit_response = client.get(
        f"/api/v1/reorder-recommendations/{recommendation_id}/audit-events"
    )

    assert spoof_response.status_code == 422
    assert pending_response.json()["review_status"] == "pending_review"
    assert approval_response.status_code == 200
    assert approval_response.json()["decision"]["decided_by"] == "trusted-reviewer-7"
    events = audit_response.json()["events"]
    assert len(events) == 2
    assert events[-1]["actor"] == "trusted-reviewer-7"
    assert (
        events[-1]["decision_id"] == approval_response.json()["decision"]["decision_id"]
    )


def test_401_and_403_emit_one_secret_safe_correlated_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    application = create_authenticated_test_app(
        settings(),
        principal=make_test_principal(
            principal_id="private-principal",
            permissions=frozenset({Permission.BUSINESS_READ}),
        ),
    )
    client = TestClient(application)
    messages: list[str] = []

    def record_message(message: object, *args: object, **kwargs: object) -> None:
        del args, kwargs
        messages.append(str(message))

    monkeypatch.setattr(logging.getLogger(HTTP_LOGGER_NAME), "info", record_message)

    invalid_token = "secret-invalid-bearer-token"
    unauthorized = client.get(
        "/api/v1/products",
        headers={
            "Authorization": f"Bearer {invalid_token}",
            REQUEST_ID_HEADER: "security-401",
        },
    )
    forbidden = client.post(
        "/api/v1/products",
        json=product_payload(),
        headers={
            "Authorization": f"Bearer {TEST_BEARER_TOKEN}",
            REQUEST_ID_HEADER: "security-403",
        },
    )

    assert unauthorized.headers[REQUEST_ID_HEADER] == "security-401"
    assert forbidden.headers[REQUEST_ID_HEADER] == "security-403"
    assert [unauthorized.status_code, forbidden.status_code] == [401, 403]
    assert len(messages) == 2
    parsed = [json.loads(message) for message in messages]
    assert [event["status_code"] for event in parsed] == [401, 403]
    assert all(event["error_category"] == "client_error" for event in parsed)
    assert all(len(event) == 7 for event in parsed)
    combined_output = " ".join(messages) + unauthorized.text + forbidden.text
    for secret in (
        invalid_token,
        TEST_BEARER_TOKEN,
        "private-principal",
        "business:read",
    ):
        assert secret not in combined_output


def test_openapi_documents_complete_permission_boundary() -> None:
    schema = TestClient(create_app(settings())).get("/openapi.json").json()
    expected_methods = {
        ("/api/v1/products", "get"),
        ("/api/v1/products", "post"),
        ("/api/v1/products/{product_id}", "get"),
        ("/api/v1/products/{product_id}/inventory", "get"),
        ("/api/v1/products/{product_id}/inventory", "put"),
        ("/api/v1/products/{product_id}/demand", "get"),
        ("/api/v1/products/{product_id}/demand", "post"),
        ("/api/v1/products/{product_id}/forecast", "get"),
        ("/api/v1/products/{product_id}/stockout-exposure", "get"),
        ("/api/v1/products/{product_id}/reorder-recommendation", "get"),
        ("/api/v1/products/{product_id}/reorder-recommendations", "post"),
        ("/api/v1/reorder-recommendations", "get"),
        ("/api/v1/reorder-recommendations/{recommendation_id}", "get"),
        (
            "/api/v1/reorder-recommendations/{recommendation_id}/audit-events",
            "get",
        ),
        ("/api/v1/reorder-recommendations/{recommendation_id}/approve", "post"),
        ("/api/v1/reorder-recommendations/{recommendation_id}/reject", "post"),
    }

    assert schema["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "description": "Signed bearer access token validated by OpsMind.",
        "scheme": "bearer",
    }
    actual_methods = {
        (path, method)
        for path, operations in schema["paths"].items()
        for method, operation in operations.items()
        if operation.get("security") == [{"BearerAuth": []}]
    }
    assert actual_methods == expected_methods
    for path, method in expected_methods:
        assert {"401", "403"} <= set(schema["paths"][path][method]["responses"])
    for public_path in ("/health", "/ready"):
        assert "security" not in schema["paths"][public_path]["get"]


def test_configured_jwt_authenticator_reaches_protected_route() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode("ascii")
    )
    issuer = "https://identity.example.test/"
    audience = "opsmind-api"
    token = jwt.encode(
        {
            "iss": issuer,
            "aud": audience,
            "sub": "signed-reviewer",
            "exp": datetime.now(UTC) + timedelta(minutes=5),
            "permissions": [Permission.BUSINESS_READ.value],
        },
        private_pem,
        algorithm="RS256",
    )
    application = create_app(
        Settings(
            environment=Environment.TEST,
            auth_issuer=issuer,
            auth_audience=audience,
            auth_public_key=SecretStr(public_pem),
        )
    )

    response = TestClient(application).get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []


def test_configured_jwks_authenticator_reaches_protected_route(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    serialized_jwk = RSAAlgorithm.to_jwk(private_key.public_key())
    jwk = cast(dict[str, object], json.loads(serialized_jwk))
    kid = "api-test-key"
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})

    def fake_fetch_data(_: object) -> dict[str, object]:
        return {"keys": [jwk]}

    monkeypatch.setattr(
        "opsmind.security_zitadel.BoundedPyJWKClient.fetch_data",
        fake_fetch_data,
    )

    issuer = "https://identity.example.test/"
    audience = "opsmind-project-123"
    roles_claim = f"urn:zitadel:iam:org:project:{audience}:roles"
    now = datetime.now(UTC)

    token = jwt.encode(
        {
            "iss": issuer,
            "aud": [audience, "frontend-client"],
            "sub": "zitadel-api-reviewer",
            "exp": now + timedelta(minutes=5),
            "iat": now,
            "nbf": now - timedelta(seconds=1),
            "jti": "api-access-token-1",
            roles_claim: [
                {
                    "opsmind.business.read": {
                        "org-1": "example.test",
                    }
                }
            ],
        },
        private_pem,
        algorithm="RS256",
        headers={"kid": kid},
    )

    application = create_app(
        Settings(
            environment=Environment.TEST,
            auth_issuer=issuer,
            auth_audience=audience,
            auth_jwks_url="https://identity.example.test/oauth/v2/keys",
        )
    )

    response = TestClient(application).get(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json() == []
