"""Tests for bounded ZITADEL release-smoke token acquisition."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from scripts.request_zitadel_smoke_token import (
    JWT_BEARER_GRANT_TYPE,
    MAX_TOKEN_RESPONSE_BYTES,
    READ_ROLE,
    SmokeTokenConfig,
    SmokeTokenError,
    request_access_token,
)

ISSUER = "https://identity.example.test"
PROJECT_ID = "123456789"
USER_ID = "987654321"
KEY_ID = "111222333"
NOW = 1_800_000_000


class FakeResponse:
    """Minimal bounded urllib response test double."""

    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def read(self, amount: int = -1) -> bytes:
        return self._payload if amount < 0 else self._payload[:amount]

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        del exc_type, exc_value, traceback


def config() -> SmokeTokenConfig:
    return SmokeTokenConfig(
        issuer=ISSUER,
        project_id=PROJECT_ID,
        user_id=USER_ID,
        key_id=KEY_ID,
    )


def private_key_and_pem() -> tuple[rsa.RSAPrivateKey, bytes]:
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return private_key, private_pem


def access_token(
    signing_key: rsa.RSAPrivateKey,
    *,
    roles: dict[str, dict[str, str]] | list[dict[str, dict[str, str]]] | None = None,
    audience: str | list[str] = PROJECT_ID,
) -> str:
    role_claim = f"urn:zitadel:iam:org:project:{PROJECT_ID}:roles"
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": audience,
        "sub": USER_ID,
        "iat": NOW,
        "nbf": NOW,
        "exp": NOW + 600,
        "jti": "smoke-jti",
        role_claim: (
            roles
            if roles is not None
            else {
                READ_ROLE: {
                    "organization-id": "organization.example.test",
                }
            }
        ),
    }

    return jwt.encode(
        claims,
        signing_key,
        algorithm="RS256",
        headers={"kid": "issuer-signing-key"},
    )


def token_response(token: str) -> bytes:
    return json.dumps(
        {
            "access_token": token,
            "token_type": "Bearer",
            "expires_in": 600,
        }
    ).encode()


def test_private_key_jwt_exchange_requests_project_audience_and_returns_jwt() -> None:
    service_key, service_pem = private_key_and_pem()
    issuer_key, _ = private_key_and_pem()
    issued_token = access_token(issuer_key)
    requests: list[tuple[object, float]] = []

    def opener(
        request: object,
        *,
        timeout: float,
    ) -> FakeResponse:
        requests.append((request, timeout))
        return FakeResponse(token_response(issued_token))

    result = request_access_token(
        config(),
        service_pem,
        opener=opener,
        now=NOW,
    )

    assert result == issued_token
    assert len(requests) == 1

    raw_request, timeout = requests[0]
    assert timeout == 10.0
    assert isinstance(raw_request, urllib.request.Request)
    assert raw_request.full_url == f"{ISSUER}/oauth/v2/token"
    assert raw_request.method == "POST"

    assert isinstance(raw_request.data, bytes)
    fields = urllib.parse.parse_qs(raw_request.data.decode("ascii"))
    assert fields["grant_type"] == [JWT_BEARER_GRANT_TYPE]
    assert fields["scope"] == [
        f"openid urn:zitadel:iam:org:project:id:{PROJECT_ID}:aud"
    ]

    assertion = fields["assertion"][0]
    assert jwt.get_unverified_header(assertion)["kid"] == KEY_ID
    assertion_claims = jwt.decode(
        assertion,
        service_key.public_key(),
        algorithms=["RS256"],
        audience=ISSUER,
        options={
            "verify_exp": False,
            "verify_iat": False,
        },
    )
    assert assertion_claims["iss"] == USER_ID
    assert assertion_claims["sub"] == USER_ID
    assert assertion_claims["iat"] == NOW
    assert assertion_claims["exp"] == NOW + 300


def test_documented_list_role_shape_is_accepted() -> None:
    _, service_pem = private_key_and_pem()
    issuer_key, _ = private_key_and_pem()
    issued_token = access_token(
        issuer_key,
        roles=[
            {
                READ_ROLE: {
                    "organization-id": "organization.example.test",
                }
            }
        ],
    )

    result = request_access_token(
        config(),
        service_pem,
        opener=lambda request, *, timeout: FakeResponse(token_response(issued_token)),
        now=NOW,
    )

    assert result == issued_token


def test_opaque_access_token_is_rejected() -> None:
    _, service_pem = private_key_and_pem()

    with pytest.raises(SmokeTokenError, match="unexpected smoke access token"):
        request_access_token(
            config(),
            service_pem,
            opener=lambda request, *, timeout: FakeResponse(
                token_response("opaque-token")
            ),
            now=NOW,
        )


def test_smoke_identity_must_have_exact_read_only_role() -> None:
    _, service_pem = private_key_and_pem()
    issuer_key, _ = private_key_and_pem()
    issued_token = access_token(
        issuer_key,
        roles={
            READ_ROLE: {
                "organization-id": "organization.example.test",
            },
            "opsmind.business.write": {
                "organization-id": "organization.example.test",
            },
        },
    )

    with pytest.raises(SmokeTokenError, match="unexpected smoke access token"):
        request_access_token(
            config(),
            service_pem,
            opener=lambda request, *, timeout: FakeResponse(
                token_response(issued_token)
            ),
            now=NOW,
        )


def test_wrong_project_audience_is_rejected() -> None:
    _, service_pem = private_key_and_pem()
    issuer_key, _ = private_key_and_pem()
    issued_token = access_token(issuer_key, audience="different-project")

    with pytest.raises(SmokeTokenError, match="unexpected smoke access token"):
        request_access_token(
            config(),
            service_pem,
            opener=lambda request, *, timeout: FakeResponse(
                token_response(issued_token)
            ),
            now=NOW,
        )


def test_oversized_token_response_is_rejected() -> None:
    _, service_pem = private_key_and_pem()

    with pytest.raises(
        SmokeTokenError,
        match="response was too large",
    ):
        request_access_token(
            config(),
            service_pem,
            opener=lambda request, *, timeout: FakeResponse(
                b"x" * (MAX_TOKEN_RESPONSE_BYTES + 1)
            ),
            now=NOW,
        )


def test_network_failure_is_normalized() -> None:
    _, service_pem = private_key_and_pem()

    def opener(
        request: object,
        *,
        timeout: float,
    ) -> FakeResponse:
        del request, timeout
        raise urllib.error.URLError("synthetic provider failure")

    with pytest.raises(
        SmokeTokenError,
        match="ZITADEL smoke-token request failed",
    ):
        request_access_token(
            config(),
            service_pem,
            opener=opener,
            now=NOW,
        )
