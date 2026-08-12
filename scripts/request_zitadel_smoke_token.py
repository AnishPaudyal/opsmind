"""Request one bounded least-privilege ZITADEL JWT smoke access token."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol, cast

import jwt

JWT_BEARER_GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
READ_ROLE = "opsmind.business.read"

MAX_PRIVATE_KEY_BYTES = 32 * 1024
MAX_TOKEN_RESPONSE_BYTES = 64 * 1024
MAX_ACCESS_TOKEN_LENGTH = 8192
REQUEST_TIMEOUT_SECONDS = 10.0
ASSERTION_LIFETIME_SECONDS = 300


class SmokeTokenError(RuntimeError):
    """Signal one bounded smoke-token acquisition failure."""


class HTTPResponse(Protocol):
    """Minimum response boundary required by the token requester."""

    def read(self, amount: int = -1) -> bytes:
        """Read at most the requested response bytes."""
        ...

    def __enter__(self) -> HTTPResponse:
        """Enter the response context."""
        ...

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        """Leave the response context."""
        ...


class URLOpener(Protocol):
    """Callable boundary for HTTPS requests."""

    def __call__(
        self,
        request: urllib.request.Request,
        *,
        timeout: float,
    ) -> HTTPResponse:
        """Open one bounded request."""
        ...


def _open_url(
    request: urllib.request.Request,
    *,
    timeout: float,
) -> HTTPResponse:
    """Adapt urllib's broader callable signature to the bounded opener protocol."""
    return cast(
        HTTPResponse,
        urllib.request.urlopen(request, timeout=timeout),
    )


@dataclass(frozen=True, slots=True)
class SmokeTokenConfig:
    """Public identity metadata needed for one smoke-token request."""

    issuer: str
    project_id: str
    user_id: str
    key_id: str


def _required_environment(name: str, *, maximum_length: int = 2048) -> str:
    value = os.environ.get(name)
    if (
        value is None
        or not value
        or value != value.strip()
        or len(value) > maximum_length
    ):
        raise SmokeTokenError("invalid smoke-token configuration")
    return value


def config_from_environment() -> SmokeTokenConfig:
    """Load and validate public smoke-identity metadata."""
    issuer = _required_environment("ZITADEL_ISSUER")
    parsed = urllib.parse.urlsplit(issuer)

    if (
        parsed.scheme != "https"
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        raise SmokeTokenError("invalid smoke-token configuration")

    return SmokeTokenConfig(
        issuer=issuer.rstrip("/"),
        project_id=_required_environment(
            "ZITADEL_PROJECT_ID",
            maximum_length=256,
        ),
        user_id=_required_environment(
            "ZITADEL_SMOKE_USER_ID",
            maximum_length=256,
        ),
        key_id=_required_environment(
            "ZITADEL_SMOKE_KEY_ID",
            maximum_length=256,
        ),
    )


def read_private_key() -> bytes:
    """Read the private key only from bounded stdin."""
    private_key = sys.stdin.buffer.read(MAX_PRIVATE_KEY_BYTES + 1)

    if not private_key or len(private_key) > MAX_PRIVATE_KEY_BYTES:
        raise SmokeTokenError("invalid smoke-token credential")

    return private_key


def build_assertion(
    config: SmokeTokenConfig,
    private_key: bytes,
    *,
    now: int | None = None,
) -> str:
    """Create the short-lived RFC 7523 assertion used only at ZITADEL."""
    issued_at = int(time.time()) if now is None else now

    return jwt.encode(
        {
            "iss": config.user_id,
            "sub": config.user_id,
            "aud": config.issuer,
            "iat": issued_at,
            "exp": issued_at + ASSERTION_LIFETIME_SECONDS,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": config.key_id},
    )


def _role_names(raw_roles: Any) -> frozenset[str]:
    if isinstance(raw_roles, dict):
        entries = [raw_roles]
    elif isinstance(raw_roles, list):
        entries = raw_roles
    else:
        raise SmokeTokenError("unexpected smoke access token")

    roles: set[str] = set()

    for entry in entries:
        if not isinstance(entry, dict):
            raise SmokeTokenError("unexpected smoke access token")

        for role_name, organizations in entry.items():
            if (
                not isinstance(role_name, str)
                or not role_name
                or role_name != role_name.strip()
                or not isinstance(organizations, dict)
                or not organizations
            ):
                raise SmokeTokenError("unexpected smoke access token")

            for organization_id, organization_domain in organizations.items():
                if (
                    not isinstance(organization_id, str)
                    or not organization_id
                    or organization_id != organization_id.strip()
                    or not isinstance(organization_domain, str)
                    or not organization_domain
                    or organization_domain != organization_domain.strip()
                ):
                    raise SmokeTokenError("unexpected smoke access token")

            roles.add(role_name)

    return frozenset(roles)


def validate_access_token(token: str, config: SmokeTokenConfig) -> None:
    """Structurally preflight the token before the API verifies it cryptographically."""
    if (
        not token
        or len(token) > MAX_ACCESS_TOKEN_LENGTH
        or any(character.isspace() for character in token)
        or len(token.split(".")) != 3
    ):
        raise SmokeTokenError("unexpected smoke access token")

    header = jwt.get_unverified_header(token)
    if header.get("alg") != "RS256":
        raise SmokeTokenError("unexpected smoke access token")

    claims = jwt.decode(
        token,
        options={
            "verify_signature": False,
            "verify_aud": False,
            "verify_exp": False,
            "verify_iat": False,
            "verify_iss": False,
            "verify_jti": False,
            "verify_nbf": False,
        },
    )

    required_claims = {"iss", "aud", "exp", "iat", "nbf", "jti", "sub"}
    if not required_claims <= claims.keys():
        raise SmokeTokenError("unexpected smoke access token")

    if claims.get("iss") != config.issuer or claims.get("sub") != config.user_id:
        raise SmokeTokenError("unexpected smoke access token")

    raw_audience = claims.get("aud")
    if isinstance(raw_audience, str):
        audiences = frozenset({raw_audience})
    elif isinstance(raw_audience, list) and all(
        isinstance(value, str) for value in raw_audience
    ):
        audiences = frozenset(raw_audience)
    else:
        raise SmokeTokenError("unexpected smoke access token")

    if config.project_id not in audiences:
        raise SmokeTokenError("unexpected smoke access token")

    role_claim = f"urn:zitadel:iam:org:project:{config.project_id}:roles"
    if _role_names(claims.get(role_claim)) != frozenset({READ_ROLE}):
        raise SmokeTokenError("unexpected smoke access token")


def request_access_token(
    config: SmokeTokenConfig,
    private_key: bytes,
    *,
    opener: URLOpener = _open_url,
    now: int | None = None,
) -> str:
    """Exchange one signed assertion for one bounded JWT access token."""
    assertion = build_assertion(config, private_key, now=now)
    scope = (
        f"openid "
        f"urn:zitadel:iam:org:project:id:{config.project_id}:aud "
        "urn:zitadel:iam:org:projects:roles"
    )

    body = urllib.parse.urlencode(
        {
            "grant_type": JWT_BEARER_GRANT_TYPE,
            "scope": scope,
            "assertion": assertion,
        }
    ).encode("ascii")

    request = urllib.request.Request(
        f"{config.issuer}/oauth/v2/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )

    try:
        with opener(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = response.read(MAX_TOKEN_RESPONSE_BYTES + 1)
    except (OSError, TimeoutError, urllib.error.URLError) as error:
        raise SmokeTokenError("ZITADEL smoke-token request failed") from error

    if len(payload) > MAX_TOKEN_RESPONSE_BYTES:
        raise SmokeTokenError("ZITADEL smoke-token response was too large")

    try:
        document = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SmokeTokenError("invalid ZITADEL smoke-token response") from error

    if not isinstance(document, dict):
        raise SmokeTokenError("invalid ZITADEL smoke-token response")

    token = document.get("access_token")
    token_type = document.get("token_type")
    expires_in = document.get("expires_in")

    if (
        not isinstance(token, str)
        or token_type != "Bearer"
        or not isinstance(expires_in, (int, float))
        or isinstance(expires_in, bool)
        or expires_in <= 0
    ):
        raise SmokeTokenError("invalid ZITADEL smoke-token response")

    validate_access_token(token, config)
    return token


def main() -> int:
    """Write only the access token to stdout; keep failures generic."""
    try:
        config = config_from_environment()
        private_key = read_private_key()
        token = request_access_token(config, private_key)
    except (SmokeTokenError, jwt.PyJWTError, TypeError, ValueError):
        print("ZITADEL smoke-token acquisition failed.", file=sys.stderr)
        return 1

    sys.stdout.write(token)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
