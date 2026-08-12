"""Tests for the ZITADEL JWT/JWKS authentication adapter."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, cast

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from jwt.warnings import InsecureKeyLengthWarning

from opsmind.security import (
    MAX_BEARER_TOKEN_LENGTH,
    AuthenticationError,
    Permission,
    TrustedPrincipal,
)
from opsmind.security_zitadel import (
    MAX_JWKS_RESPONSE_BYTES,
    BoundedPyJWKClient,
    ZitadelJWTAuthenticationConfig,
    ZitadelJWTAuthenticator,
)

ISSUER = "https://identity.example.test/"
AUDIENCE = "opsmind-project-123"
JWKS_URL = "https://identity.example.test/oauth/v2/keys"
KID = "signing-key-1"
ROLES_CLAIM = f"urn:zitadel:iam:org:project:{AUDIENCE}:roles"


@pytest.fixture(scope="module")
def signing_keys() -> tuple[str, str]:
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
    return private_pem, public_pem


def config() -> ZitadelJWTAuthenticationConfig:
    return ZitadelJWTAuthenticationConfig(
        issuer=ISSUER,
        audience=AUDIENCE,
        jwks_url=JWKS_URL,
    )


def access_token_claims(**overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": [AUDIENCE, "frontend-client"],
        "sub": "zitadel-user-123",
        "exp": now + timedelta(minutes=5),
        "iat": now,
        "nbf": now - timedelta(seconds=1),
        "jti": "access-token-123",
        ROLES_CLAIM: [
            {"opsmind.business.read": {"org-1": "example.test"}},
            {"opsmind.business.write": {"org-1": "example.test"}},
            {"opsmind.recommendation.decide": {"org-1": "example.test"}},
            {"unknown.role": {"org-1": "example.test"}},
        ],
    }
    claims.update(overrides)
    return claims


def encode_token(
    private_key: str,
    *,
    claims: dict[str, Any] | None = None,
    algorithm: str = "RS256",
    kid: str = KID,
) -> str:
    return jwt.encode(
        access_token_claims() if claims is None else claims,
        private_key,
        algorithm=algorithm,
        headers={"kid": kid},
    )


class StaticKeyResolver:
    def __init__(self, public_key: str) -> None:
        self.public_key = public_key
        self.requested_kids: list[str] = []

    def get_signing_key(self, kid: str) -> Any:
        self.requested_kids.append(kid)
        return SimpleNamespace(key=self.public_key)


def authenticator(public_key: str) -> tuple[ZitadelJWTAuthenticator, StaticKeyResolver]:
    resolver = StaticKeyResolver(public_key)
    return ZitadelJWTAuthenticator(config(), resolver), resolver


def test_zitadel_authenticator_maps_only_exact_known_roles(
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, resolver = authenticator(public_key)

    principal = configured.authenticate(encode_token(private_key))

    assert principal == TrustedPrincipal(
        principal_id="zitadel-user-123",
        permissions=frozenset(
            {
                Permission.BUSINESS_READ,
                Permission.BUSINESS_WRITE,
                Permission.RECOMMENDATION_DECIDE,
            }
        ),
    )
    assert resolver.requested_kids == [KID]


def test_zitadel_authenticator_accepts_documented_direct_object_role_shape(
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, _ = authenticator(public_key)

    claims = access_token_claims(
        **{
            ROLES_CLAIM: {
                "opsmind.business.read": {"org-1": "example.test"},
                "unknown.role": {"org-1": "example.test"},
            }
        }
    )

    principal = configured.authenticate(encode_token(private_key, claims=claims))

    assert principal.permissions == frozenset({Permission.BUSINESS_READ})


def test_zitadel_authenticator_accepts_valid_token_without_roles(
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, _ = authenticator(public_key)
    claims = access_token_claims()
    del claims[ROLES_CLAIM]

    principal = configured.authenticate(encode_token(private_key, claims=claims))

    assert principal.permissions == frozenset()


@pytest.mark.parametrize(
    "roles",
    [
        ["opsmind.business.read"],
        [{"opsmind.business.read": "org-1"}],
        [{"opsmind.business.read": {}}],
        [{"opsmind.business.read": {"": "example.test"}}],
        [{"opsmind.business.read": {"org-1": ""}}],
        [{"opsmind.business.read": {"org-1": 7}}],
    ],
)
def test_zitadel_authenticator_rejects_malformed_role_claim(
    roles: object,
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, _ = authenticator(public_key)

    with pytest.raises(AuthenticationError):
        configured.authenticate(
            encode_token(
                private_key,
                claims=access_token_claims(**{ROLES_CLAIM: roles}),
            )
        )


@pytest.mark.parametrize("missing_claim", ["jti", "nbf", "iat", "exp", "sub"])
def test_zitadel_authenticator_requires_access_token_claims(
    missing_claim: str,
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, _ = authenticator(public_key)
    claims = access_token_claims()
    del claims[missing_claim]

    with pytest.raises(AuthenticationError):
        configured.authenticate(encode_token(private_key, claims=claims))


def test_zitadel_authenticator_rejects_wrong_audience(
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, _ = authenticator(public_key)

    with pytest.raises(AuthenticationError):
        configured.authenticate(
            encode_token(
                private_key,
                claims=access_token_claims(aud=["another-project"]),
            )
        )


def test_zitadel_authenticator_rejects_disallowed_algorithm_before_key_lookup(
    signing_keys: tuple[str, str],
) -> None:
    _, public_key = signing_keys
    configured, resolver = authenticator(public_key)
    token = jwt.encode(
        access_token_claims(),
        "attacker-secret-with-at-least-32-bytes",
        algorithm="HS256",
        headers={"kid": KID},
    )

    with pytest.raises(AuthenticationError):
        configured.authenticate(token)

    assert resolver.requested_kids == []


@pytest.mark.parametrize("kid", ["", " padded ", "x" * 129])
def test_zitadel_authenticator_rejects_invalid_kid_before_lookup(
    kid: str,
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, resolver = authenticator(public_key)

    with pytest.raises(AuthenticationError):
        configured.authenticate(encode_token(private_key, kid=kid))

    assert resolver.requested_kids == []


@pytest.mark.parametrize(
    ("issuer", "jwks_url"),
    [
        ("http://identity.example.test/", JWKS_URL),
        (ISSUER, "http://identity.example.test/oauth/v2/keys"),
        (ISSUER, "https://attacker.example.test/oauth/v2/keys"),
        (ISSUER, "file:///tmp/jwks.json"),
    ],
)
def test_zitadel_configuration_rejects_untrusted_jwks_boundaries(
    issuer: str,
    jwks_url: str,
) -> None:
    with pytest.raises(ValueError):
        ZitadelJWTAuthenticationConfig(
            issuer=issuer,
            audience=AUDIENCE,
            jwks_url=jwks_url,
        )


class FakeResponse:
    def __init__(
        self,
        payload: bytes,
        *,
        content_length: str | None = None,
    ) -> None:
        self.payload = payload
        self.headers: dict[str, str] = {}
        if content_length is not None:
            self.headers["Content-Length"] = content_length

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def read(self, size: int = -1) -> bytes:
        return self.payload if size < 0 else self.payload[:size]


def test_bounded_jwks_client_accepts_small_json_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b'{"keys":[]}'
    response = FakeResponse(payload, content_length=str(len(payload)))
    monkeypatch.setattr(
        "opsmind.security_zitadel.urllib.request.urlopen",
        lambda *args, **kwargs: response,
    )
    client = BoundedPyJWKClient(JWKS_URL)

    assert client.fetch_data() == {"keys": []}


def test_bounded_jwks_client_rejects_oversized_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = b"x" * (MAX_JWKS_RESPONSE_BYTES + 1)
    response = FakeResponse(payload)
    monkeypatch.setattr(
        "opsmind.security_zitadel.urllib.request.urlopen",
        lambda *args, **kwargs: response,
    )
    client = BoundedPyJWKClient(JWKS_URL)

    with pytest.raises(PyJWKClientError, match="size limit"):
        client.fetch_data()


def rsa_jwk(*, kid: str) -> dict[str, Any]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    serialized = RSAAlgorithm.to_jwk(public_key)
    raw_jwk = json.loads(serialized) if isinstance(serialized, str) else serialized
    jwk = cast(dict[str, Any], raw_jwk)
    jwk.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return jwk


class SequencedJWKClient(BoundedPyJWKClient):
    def __init__(self, responses: list[dict[str, Any]]) -> None:
        super().__init__(JWKS_URL)
        self.responses = responses
        self.fetch_count = 0

    def fetch_data(self) -> Any:
        index = min(self.fetch_count, len(self.responses) - 1)
        self.fetch_count += 1
        data: Any = self.responses[index]
        if self.jwk_set_cache is not None:
            self.jwk_set_cache.put(data)
        return data


def test_unknown_kid_causes_exactly_one_forced_jwks_refresh() -> None:
    client = SequencedJWKClient(
        [
            {"keys": [rsa_jwk(kid="old-key")]},
            {"keys": [rsa_jwk(kid="new-key")]},
        ]
    )

    signing_key = client.get_signing_key("new-key")

    assert signing_key.key_id == "new-key"
    assert client.fetch_count == 2


def test_zitadel_authenticator_rejects_missing_kid_before_lookup(
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, resolver = authenticator(public_key)
    token = jwt.encode(
        access_token_claims(),
        private_key,
        algorithm="RS256",
        headers={"typ": "JWT"},
    )

    with pytest.raises(AuthenticationError):
        configured.authenticate(token)

    assert resolver.requested_kids == []


def test_zitadel_authenticator_rejects_oversized_token_before_lookup(
    signing_keys: tuple[str, str],
) -> None:
    _, public_key = signing_keys
    configured, resolver = authenticator(public_key)

    with pytest.raises(AuthenticationError):
        configured.authenticate("x" * (MAX_BEARER_TOKEN_LENGTH + 1))

    assert resolver.requested_kids == []


@pytest.mark.parametrize(
    "claims",
    [
        access_token_claims(iss="https://attacker.example.test/"),
        access_token_claims(exp=datetime.now(UTC) - timedelta(seconds=1)),
        access_token_claims(nbf=datetime.now(UTC) + timedelta(minutes=5)),
        access_token_claims(jti=""),
        access_token_claims(jti="x" * 257),
    ],
)
def test_zitadel_authenticator_rejects_invalid_verified_claims(
    claims: dict[str, Any],
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    configured, _ = authenticator(public_key)

    with pytest.raises(AuthenticationError):
        configured.authenticate(encode_token(private_key, claims=claims))


def test_zitadel_authenticator_rejects_invalid_signature(
    signing_keys: tuple[str, str],
) -> None:
    _, trusted_public_key = signing_keys
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    attacker_private_pem = attacker_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    configured, _ = authenticator(trusted_public_key)

    with pytest.raises(AuthenticationError):
        configured.authenticate(encode_token(attacker_private_pem))


def test_zitadel_authenticator_rejects_undersized_rsa_key() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")
    serialized = RSAAlgorithm.to_jwk(private_key.public_key())
    jwk = json.loads(serialized) if isinstance(serialized, str) else serialized
    jwk.update({"kid": KID, "use": "sig", "alg": "RS256"})
    signing_key = jwt.PyJWK.from_dict(jwk)

    class Resolver:
        def get_signing_key(self, kid: str) -> Any:
            assert kid == KID
            return signing_key

    configured = ZitadelJWTAuthenticator(config(), Resolver())
    with pytest.warns(InsecureKeyLengthWarning):
        token = encode_token(private_pem)

    with pytest.raises(AuthenticationError):
        configured.authenticate(token)


def test_bounded_jwks_client_rejects_malformed_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(b'{"keys": [}')
    monkeypatch.setattr(
        "opsmind.security_zitadel.urllib.request.urlopen",
        lambda *args, **kwargs: response,
    )
    client = BoundedPyJWKClient(JWKS_URL)

    with pytest.raises(PyJWKClientError, match="valid JSON"):
        client.fetch_data()


def test_bounded_jwks_client_rejects_declared_oversized_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    response = FakeResponse(
        b'{"keys":[]}',
        content_length=str(MAX_JWKS_RESPONSE_BYTES + 1),
    )
    monkeypatch.setattr(
        "opsmind.security_zitadel.urllib.request.urlopen",
        lambda *args, **kwargs: response,
    )
    client = BoundedPyJWKClient(JWKS_URL)

    with pytest.raises(PyJWKClientError, match="size limit"):
        client.fetch_data()


def test_bounded_jwks_client_normalizes_network_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_urlopen(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise URLError("synthetic offline condition")

    from urllib.error import URLError

    monkeypatch.setattr(
        "opsmind.security_zitadel.urllib.request.urlopen",
        fail_urlopen,
    )
    client = BoundedPyJWKClient(JWKS_URL)

    with pytest.raises(
        PyJWKClientConnectionError,
        match="Unable to fetch trusted JWKS",
    ):
        client.fetch_data()


def test_unknown_kid_fails_after_exactly_one_forced_refresh() -> None:
    client = SequencedJWKClient(
        [
            {"keys": [rsa_jwk(kid="old-key")]},
            {"keys": [rsa_jwk(kid="still-not-requested-key")]},
        ]
    )

    with pytest.raises(PyJWKClientError):
        client.get_signing_key("missing-key")

    assert client.fetch_count == 2
