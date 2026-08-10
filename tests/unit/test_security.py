"""Tests for trusted principals and signed JWT authentication."""

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.warnings import InsecureKeyLengthWarning

from opsmind.security import (
    MAX_BEARER_TOKEN_LENGTH,
    AuthenticationError,
    DenyAllAuthenticator,
    JWTAuthenticationConfig,
    JWTAuthenticator,
    Permission,
    TrustedPrincipal,
)

ISSUER = "https://identity.example.test/"
AUDIENCE = "opsmind-api"


@pytest.fixture(scope="module")
def signing_keys() -> tuple[str, str]:
    """Generate synthetic RSA keys without storing private test material."""
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


def token_claims(**overrides: Any) -> dict[str, Any]:
    """Return one valid synthetic token claim set with explicit overrides."""
    now = datetime.now(UTC)
    claims: dict[str, Any] = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": "reviewer-123",
        "exp": now + timedelta(minutes=5),
        "permissions": [
            Permission.BUSINESS_READ.value,
            Permission.RECOMMENDATION_DECIDE.value,
        ],
    }
    claims.update(overrides)
    return claims


def encode_token(
    private_key: str,
    *,
    claims: dict[str, Any] | None = None,
    algorithm: str = "RS256",
) -> str:
    """Encode one synthetic token with the selected test algorithm."""
    return jwt.encode(
        token_claims() if claims is None else claims,
        private_key,
        algorithm=algorithm,
    )


def jwt_authenticator(public_key: str) -> JWTAuthenticator:
    """Return the configured production authenticator over a synthetic key."""
    return JWTAuthenticator(
        JWTAuthenticationConfig(
            issuer=ISSUER,
            audience=AUDIENCE,
            public_key=public_key,
        )
    )


def test_trusted_principal_is_immutable_and_bounded() -> None:
    principal = TrustedPrincipal(
        principal_id="reviewer-123",
        permissions=frozenset({Permission.BUSINESS_READ}),
    )

    assert principal.principal_id == "reviewer-123"
    assert principal.permissions == frozenset({Permission.BUSINESS_READ})
    with pytest.raises(AttributeError):
        principal.principal_id = "attacker"  # type: ignore[misc]


@pytest.mark.parametrize(
    "principal_id",
    ["", " leading", "trailing ", "contains space", "a" * 129, "bad?value"],
)
def test_trusted_principal_rejects_invalid_identifiers(principal_id: str) -> None:
    with pytest.raises(ValueError, match="bounded identity"):
        TrustedPrincipal(principal_id=principal_id, permissions=frozenset())


def test_trusted_principal_rejects_mutable_or_unknown_permissions() -> None:
    with pytest.raises(ValueError, match="immutable set"):
        TrustedPrincipal(
            principal_id="reviewer-123",
            permissions={Permission.BUSINESS_READ},  # type: ignore[arg-type]
        )


def test_jwt_authenticator_returns_only_bounded_trusted_claims(
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    token = encode_token(
        private_key,
        claims=token_claims(
            permissions=[
                Permission.BUSINESS_READ.value,
                "unknown:permission",
                Permission.RECOMMENDATION_DECIDE.value,
            ],
            email="private@example.test",
        ),
    )

    principal = jwt_authenticator(public_key).authenticate(token)

    assert principal == TrustedPrincipal(
        principal_id="reviewer-123",
        permissions=frozenset(
            {Permission.BUSINESS_READ, Permission.RECOMMENDATION_DECIDE}
        ),
    )
    assert not hasattr(principal, "email")


@pytest.mark.parametrize(
    "claims_override",
    [
        {"iss": "https://attacker.example.test/"},
        {"aud": "another-api"},
        {"aud": [AUDIENCE]},
        {"exp": datetime.now(UTC) - timedelta(seconds=1)},
        {"nbf": datetime.now(UTC) + timedelta(minutes=5)},
        {"sub": ""},
        {"sub": "a" * 129},
        {"permissions": "business:read"},
        {"permissions": [Permission.BUSINESS_READ.value, 7]},
    ],
)
def test_jwt_authenticator_rejects_invalid_claims(
    claims_override: dict[str, Any],
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    token = encode_token(private_key, claims=token_claims(**claims_override))

    with pytest.raises(AuthenticationError):
        jwt_authenticator(public_key).authenticate(token)


def test_jwt_authenticator_rejects_non_string_subject_defensively(
    signing_keys: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, public_key = signing_keys

    def decoded_non_string_subject(*args: object, **kwargs: object) -> dict[str, Any]:
        del args, kwargs
        return {"sub": 7, "permissions": []}

    monkeypatch.setattr(jwt, "decode", decoded_non_string_subject)

    with pytest.raises(AuthenticationError):
        jwt_authenticator(public_key).authenticate("synthetic.token.value")


@pytest.mark.parametrize("missing_claim", ["iss", "aud", "exp", "sub"])
def test_jwt_authenticator_requires_core_claims(
    missing_claim: str,
    signing_keys: tuple[str, str],
) -> None:
    private_key, public_key = signing_keys
    claims = token_claims()
    del claims[missing_claim]

    with pytest.raises(AuthenticationError):
        jwt_authenticator(public_key).authenticate(
            encode_token(private_key, claims=claims)
        )


def test_jwt_authenticator_rejects_invalid_signature(
    signing_keys: tuple[str, str],
) -> None:
    _, trusted_public_key = signing_keys
    attacker_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    attacker_private_pem = attacker_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("ascii")

    with pytest.raises(AuthenticationError):
        jwt_authenticator(trusted_public_key).authenticate(
            encode_token(attacker_private_pem)
        )


def test_jwt_authenticator_rejects_undersized_rsa_verification_key() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
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
    with pytest.warns(InsecureKeyLengthWarning):
        token = encode_token(private_pem)

    with pytest.raises(AuthenticationError):
        jwt_authenticator(public_pem).authenticate(token)


def test_jwt_authenticator_rejects_disallowed_and_unsigned_algorithms(
    signing_keys: tuple[str, str],
) -> None:
    _, public_key = signing_keys
    symmetric_token = jwt.encode(
        token_claims(),
        "attacker-secret-with-at-least-32-bytes",
        algorithm="HS256",
    )
    unsigned_token = jwt.encode(token_claims(), key="", algorithm="none")

    for token in (symmetric_token, unsigned_token):
        with pytest.raises(AuthenticationError):
            jwt_authenticator(public_key).authenticate(token)


def test_jwt_authenticator_rejects_malformed_or_oversized_tokens(
    signing_keys: tuple[str, str],
) -> None:
    _, public_key = signing_keys
    authenticator = jwt_authenticator(public_key)

    for token in ("", "not-a-jwt", "x" * (MAX_BEARER_TOKEN_LENGTH + 1)):
        with pytest.raises(AuthenticationError):
            authenticator.authenticate(token)


def test_authentication_configuration_is_secret_safe_and_bounded(
    signing_keys: tuple[str, str],
) -> None:
    _, public_key = signing_keys
    config = JWTAuthenticationConfig(
        issuer=ISSUER,
        audience=AUDIENCE,
        public_key=public_key,
    )

    assert public_key not in repr(config)
    with pytest.raises(ValueError, match="RS256"):
        JWTAuthenticationConfig(
            issuer=ISSUER,
            audience=AUDIENCE,
            public_key=public_key,
            algorithm="HS256",
        )
    with pytest.raises(ValueError, match="between 0 and 60"):
        JWTAuthenticationConfig(
            issuer=ISSUER,
            audience=AUDIENCE,
            public_key=public_key,
            clock_leeway_seconds=61,
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("issuer", "", "issuer"),
        ("issuer", " padded ", "issuer"),
        ("audience", "", "audience"),
        ("audience", " padded ", "audience"),
        ("public_key", "   ", "public_key"),
    ],
)
def test_authentication_configuration_rejects_invalid_required_values(
    field: str,
    value: str,
    message: str,
    signing_keys: tuple[str, str],
) -> None:
    _, public_key = signing_keys
    values: dict[str, Any] = {
        "issuer": ISSUER,
        "audience": AUDIENCE,
        "public_key": public_key,
    }
    values[field] = value

    with pytest.raises(ValueError, match=message):
        JWTAuthenticationConfig(**values)


def test_deny_all_authenticator_always_fails_closed() -> None:
    with pytest.raises(AuthenticationError):
        DenyAllAuthenticator().authenticate("any-token")
