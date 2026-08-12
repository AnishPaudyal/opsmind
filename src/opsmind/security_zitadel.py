"""ZITADEL JWT access-token authentication over a bounded JWKS client."""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse

import jwt
from jwt import PyJWKClient, PyJWTError
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError

from opsmind.security import (
    MAX_BEARER_TOKEN_LENGTH,
    AuthenticationError,
    Permission,
    TrustedPrincipal,
)

MAX_JWKS_RESPONSE_BYTES = 256 * 1024
MAX_KEY_ID_LENGTH = 128
MAX_JTI_LENGTH = 256

_ROLE_PERMISSION_MAP = {
    "opsmind.business.read": Permission.BUSINESS_READ,
    "opsmind.business.write": Permission.BUSINESS_WRITE,
    "opsmind.recommendation.decide": Permission.RECOMMENDATION_DECIDE,
}


class SigningKey(Protocol):
    """Minimal signing-key shape consumed by the authenticator."""

    key: Any


class SigningKeyResolver(Protocol):
    """Resolve one trusted signing key by key ID."""

    def get_signing_key(self, kid: str) -> SigningKey:
        """Return the trusted signing key for ``kid``."""
        ...


@dataclass(frozen=True, slots=True, repr=False)
class ZitadelJWTAuthenticationConfig:
    """Validated ZITADEL JWT/JWKS authentication boundary."""

    issuer: str
    audience: str
    jwks_url: str
    algorithm: str = "RS256"
    clock_leeway_seconds: int = 0
    jwks_timeout_seconds: float = 5.0
    jwks_cache_seconds: float = 300.0

    def __post_init__(self) -> None:
        if not self.issuer or self.issuer != self.issuer.strip():
            raise ValueError("issuer must be non-empty without surrounding whitespace")
        if not self.audience or self.audience != self.audience.strip():
            raise ValueError(
                "audience must be non-empty without surrounding whitespace"
            )
        if not self.jwks_url or self.jwks_url != self.jwks_url.strip():
            raise ValueError(
                "jwks_url must be non-empty without surrounding whitespace"
            )
        if self.algorithm != "RS256":
            raise ValueError("algorithm must be RS256")
        if not 0 <= self.clock_leeway_seconds <= 60:
            raise ValueError("clock_leeway_seconds must be between 0 and 60")
        if not 0 < self.jwks_timeout_seconds <= 10:
            raise ValueError("jwks_timeout_seconds must be between 0 and 10")
        if not 0 < self.jwks_cache_seconds <= 3600:
            raise ValueError("jwks_cache_seconds must be between 0 and 3600")

        issuer_origin = _validated_https_origin(self.issuer, "issuer")
        jwks_origin = _validated_https_origin(self.jwks_url, "jwks_url")
        if issuer_origin != jwks_origin:
            raise ValueError("JWKS URL must use the configured issuer host")

    @property
    def roles_claim(self) -> str:
        """Return the exact project-scoped ZITADEL roles claim."""
        return f"urn:zitadel:iam:org:project:{self.audience}:roles"


def _validated_https_origin(value: str, field_name: str) -> tuple[str, int]:
    parsed = urlparse(value)
    if (
        parsed.scheme.lower() != "https"
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        raise ValueError(f"{field_name} must be a credential-free HTTPS URL")
    try:
        port = parsed.port or 443
    except ValueError:
        raise ValueError(f"{field_name} must contain a valid port") from None
    return parsed.hostname.lower(), port


class BoundedPyJWKClient(PyJWKClient):
    """PyJWT JWKS client with a bounded response body."""

    def __init__(
        self,
        uri: str,
        *,
        timeout: float = 5.0,
        lifespan: float = 300.0,
        max_response_bytes: int = MAX_JWKS_RESPONSE_BYTES,
    ) -> None:
        if max_response_bytes <= 0:
            raise ValueError("max_response_bytes must be positive")
        self._max_response_bytes = max_response_bytes
        super().__init__(
            uri,
            cache_keys=False,
            cache_jwk_set=True,
            lifespan=lifespan,
            timeout=timeout,
        )

    def fetch_data(self) -> Any:
        """Fetch and cache one bounded JWKS document."""
        try:
            request = urllib.request.Request(url=self.uri, headers=self.headers)
            with urllib.request.urlopen(
                request,
                timeout=self.timeout,
                context=self.ssl_context,
            ) as response:
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        declared_length = int(content_length)
                    except (TypeError, ValueError):
                        declared_length = None
                    if (
                        declared_length is not None
                        and declared_length > self._max_response_bytes
                    ):
                        raise PyJWKClientError(
                            "JWKS response exceeds the configured size limit"
                        )

                payload = response.read(self._max_response_bytes + 1)
                if len(payload) > self._max_response_bytes:
                    raise PyJWKClientError(
                        "JWKS response exceeds the configured size limit"
                    )
        except (URLError, TimeoutError) as exc:
            if isinstance(exc, HTTPError):
                exc.close()
            raise PyJWKClientConnectionError("Unable to fetch trusted JWKS") from exc

        try:
            jwk_set = json.loads(payload)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise PyJWKClientError("JWKS response is not valid JSON") from exc

        if self.jwk_set_cache is not None:
            self.jwk_set_cache.put(jwk_set)
        return jwk_set


class ZitadelJWTAuthenticator:
    """Validate ZITADEL RS256 JWT access tokens into trusted principals."""

    def __init__(
        self,
        config: ZitadelJWTAuthenticationConfig,
        key_resolver: SigningKeyResolver | None = None,
    ) -> None:
        self._config = config
        self._key_resolver = (
            key_resolver
            if key_resolver is not None
            else BoundedPyJWKClient(
                config.jwks_url,
                timeout=config.jwks_timeout_seconds,
                lifespan=config.jwks_cache_seconds,
            )
        )

    def authenticate(self, token: str) -> TrustedPrincipal:
        """Validate one JWT access token and map exact ZITADEL roles."""
        if not token or len(token) > MAX_BEARER_TOKEN_LENGTH:
            raise AuthenticationError

        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != self._config.algorithm:
                raise ValueError("unexpected token algorithm")

            kid = header.get("kid")
            if (
                not isinstance(kid, str)
                or not kid
                or kid != kid.strip()
                or len(kid) > MAX_KEY_ID_LENGTH
            ):
                raise ValueError("invalid key identifier")

            signing_key = self._key_resolver.get_signing_key(kid)

            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=[self._config.algorithm],
                audience=self._config.audience,
                issuer=self._config.issuer,
                leeway=self._config.clock_leeway_seconds,
                options={
                    "require": [
                        "iss",
                        "aud",
                        "exp",
                        "iat",
                        "nbf",
                        "jti",
                        "sub",
                    ],
                    "verify_signature": True,
                    "verify_iss": True,
                    "verify_aud": True,
                    "verify_exp": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                    "verify_sub": True,
                    "strict_aud": False,
                    "enforce_minimum_key_length": True,
                },
            )

            principal_id = claims["sub"]
            token_id = claims["jti"]
            if not isinstance(principal_id, str):
                raise ValueError("subject must be a string")
            if (
                not isinstance(token_id, str)
                or not token_id
                or len(token_id) > MAX_JTI_LENGTH
            ):
                raise ValueError("jti must satisfy the bounded token contract")

            permissions = _parse_zitadel_roles(claims.get(self._config.roles_claim, []))
            return TrustedPrincipal(
                principal_id=principal_id,
                permissions=permissions,
            )
        except (
            PyJWTError,
            PyJWKClientError,
            KeyError,
            TypeError,
            ValueError,
        ):
            raise AuthenticationError from None


def _parse_zitadel_roles(raw_roles: Any) -> frozenset[Permission]:
    """Map exact trusted ZITADEL project roles from documented claim shapes."""
    if isinstance(raw_roles, dict):
        role_entries = [raw_roles]
    elif isinstance(raw_roles, list):
        role_entries = raw_roles
    else:
        raise ValueError("roles claim must be an object or list of objects")

    permissions: set[Permission] = set()

    for role_entry in role_entries:
        if not isinstance(role_entry, dict):
            raise ValueError("roles claim entries must be objects")

        for role, organizations in role_entry.items():
            if (
                not isinstance(role, str)
                or not role
                or not isinstance(organizations, dict)
                or not organizations
            ):
                raise ValueError(
                    "roles claim must contain role-to-organization mappings"
                )

            if any(
                not isinstance(organization_id, str)
                or not organization_id
                or not isinstance(domain, str)
                or not domain
                for organization_id, domain in organizations.items()
            ):
                raise ValueError(
                    "role organization mappings must contain non-empty strings"
                )

            permission = _ROLE_PERMISSION_MAP.get(role)
            if permission is not None:
                permissions.add(permission)

    return frozenset(permissions)
