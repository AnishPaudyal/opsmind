"""Provider-agnostic trusted-principal authentication primitives."""

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

import jwt
from jwt import PyJWTError

MAX_BEARER_TOKEN_LENGTH = 8192
MAX_PRINCIPAL_ID_LENGTH = 128
PERMISSIONS_CLAIM = "permissions"

_PRINCIPAL_ID_PATTERN = re.compile(
    rf"[A-Za-z0-9][A-Za-z0-9._:@/-]{{0,{MAX_PRINCIPAL_ID_LENGTH - 1}}}"
)


class Permission(StrEnum):
    """Bounded OpsMind application permissions."""

    BUSINESS_READ = "business:read"
    BUSINESS_WRITE = "business:write"
    RECOMMENDATION_DECIDE = "recommendation:decide"


@dataclass(frozen=True, slots=True)
class TrustedPrincipal:
    """Minimal identity and permissions derived from verified credentials."""

    principal_id: str
    permissions: frozenset[Permission]

    def __post_init__(self) -> None:
        if _PRINCIPAL_ID_PATTERN.fullmatch(self.principal_id) is None:
            raise ValueError("principal_id must satisfy the bounded identity contract")
        if not isinstance(self.permissions, frozenset) or any(
            not isinstance(permission, Permission) for permission in self.permissions
        ):
            raise ValueError("permissions must be an immutable set of permissions")


class AuthenticationError(Exception):
    """Signal a generic credential-validation failure without public detail."""


class Authenticator(Protocol):
    """Validate one bearer credential and return a trusted principal."""

    def authenticate(self, token: str) -> TrustedPrincipal:
        """Return a principal or raise ``AuthenticationError``."""
        ...


@dataclass(frozen=True, slots=True, repr=False)
class JWTAuthenticationConfig:
    """Validated configuration for one trusted JWT issuer and public key."""

    issuer: str
    audience: str
    public_key: str
    algorithm: str = "RS256"
    clock_leeway_seconds: int = 0

    def __post_init__(self) -> None:
        if not self.issuer or self.issuer != self.issuer.strip():
            raise ValueError("issuer must be non-empty without surrounding whitespace")
        if not self.audience or self.audience != self.audience.strip():
            raise ValueError(
                "audience must be non-empty without surrounding whitespace"
            )
        if not self.public_key.strip():
            raise ValueError("public_key must not be empty")
        if self.algorithm != "RS256":
            raise ValueError("algorithm must be RS256")
        if not 0 <= self.clock_leeway_seconds <= 60:
            raise ValueError("clock_leeway_seconds must be between 0 and 60")


class DenyAllAuthenticator:
    """Fail closed when protected-route authentication is not configured."""

    def authenticate(self, token: str) -> TrustedPrincipal:
        """Reject every credential without inspecting or retaining it."""
        del token
        raise AuthenticationError


class JWTAuthenticator:
    """Validate RS256 bearer tokens against one configured trust boundary."""

    def __init__(self, config: JWTAuthenticationConfig) -> None:
        self._config = config

    def authenticate(self, token: str) -> TrustedPrincipal:
        """Validate a bearer token and map bounded claims to a principal."""
        if not token or len(token) > MAX_BEARER_TOKEN_LENGTH:
            raise AuthenticationError
        try:
            claims = jwt.decode(
                token,
                self._config.public_key,
                algorithms=[self._config.algorithm],
                audience=self._config.audience,
                issuer=self._config.issuer,
                leeway=self._config.clock_leeway_seconds,
                options={
                    "require": ["iss", "aud", "exp", "sub"],
                    "verify_signature": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_sub": True,
                    "strict_aud": True,
                    "enforce_minimum_key_length": True,
                },
            )
            principal_id = claims["sub"]
            permissions = _parse_permissions(claims.get(PERMISSIONS_CLAIM, []))
            if not isinstance(principal_id, str):
                raise ValueError("subject must be a string")
            return TrustedPrincipal(
                principal_id=principal_id,
                permissions=permissions,
            )
        except (PyJWTError, KeyError, TypeError, ValueError):
            raise AuthenticationError from None


def _parse_permissions(raw_permissions: Any) -> frozenset[Permission]:
    """Map a strict string-list claim to known permissions only."""
    if not isinstance(raw_permissions, list) or any(
        not isinstance(value, str) for value in raw_permissions
    ):
        raise ValueError("permissions claim must be a list of strings")
    supported_values = {permission.value: permission for permission in Permission}
    return frozenset(
        supported_values[value]
        for value in raw_permissions
        if value in supported_values
    )
