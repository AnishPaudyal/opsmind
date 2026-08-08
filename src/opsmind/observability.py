"""Bounded HTTP request observability primitives and middleware."""

import json
import logging
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from time import monotonic
from typing import Literal
from uuid import uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

HTTP_LOGGER_NAME = "opsmind.http"
REQUEST_ID_HEADER = "X-Request-ID"
REQUEST_ID_STATE_KEY = "request_id"
ERROR_CATEGORY_STATE_KEY = "http_error_category"

_HTTP_LOG_HANDLER_NAME = "opsmind.http.stderr"
_REQUEST_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
_REQUEST_ID_HEADER_BYTES = REQUEST_ID_HEADER.lower().encode("ascii")


class ErrorCategory(StrEnum):
    """Bounded error classifications for governed HTTP request events."""

    NONE = "none"
    CLIENT_ERROR = "client_error"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    SERVER_ERROR = "server_error"
    UNHANDLED_EXCEPTION = "unhandled_exception"
    STREAMING_ERROR = "streaming_error"


@dataclass(frozen=True, slots=True)
class HTTPRequestEvent:
    """One bounded, machine-serializable HTTP request event."""

    request_id: str
    method: str
    route: str
    status_code: int
    duration_ms: float
    error_category: ErrorCategory
    event: Literal["http_request"] = field(default="http_request", init=False)


def is_valid_request_id(value: str) -> bool:
    """Return whether a caller request ID satisfies the public contract."""
    return _REQUEST_ID_PATTERN.fullmatch(value) is not None


def resolve_request_id(values: Sequence[str]) -> str:
    """Preserve one valid caller request ID or generate a server-owned UUID."""
    if len(values) == 1 and is_valid_request_id(values[0]):
        return values[0]
    return str(uuid4())


def classify_http_status(status_code: int) -> ErrorCategory:
    """Classify an ordinary completed HTTP response by status."""
    if status_code < 400:
        return ErrorCategory.NONE
    if status_code < 500:
        return ErrorCategory.CLIENT_ERROR
    return ErrorCategory.SERVER_ERROR


def serialize_http_request_event(event: HTTPRequestEvent) -> dict[str, object]:
    """Return the governed event fields as a JSON-compatible dictionary."""
    return {
        "event": event.event,
        "request_id": event.request_id,
        "method": event.method,
        "route": event.route,
        "status_code": event.status_code,
        "duration_ms": event.duration_ms,
        "error_category": event.error_category.value,
    }


def classify_route(scope: Scope) -> str:
    """Return a matched route template or a bounded fallback classification."""
    fastapi_scope = scope.get("fastapi")
    if isinstance(fastapi_scope, dict):
        effective_route = fastapi_scope.get("effective_route_context")
        template = getattr(effective_route, "path_format", None)
        if isinstance(template, str) and template:
            return template

    route = scope.get("route")
    if route is not None:
        for attribute in ("path_format", "path"):
            template = getattr(route, attribute, None)
            if isinstance(template, str) and template:
                return template
        return "unknown"
    if "router" in scope:
        return "unmatched"
    return "unknown"


def configure_http_logger() -> logging.Logger:
    """Configure and return the dedicated request logger idempotently."""
    logger = logging.getLogger(HTTP_LOGGER_NAME)
    if not any(
        handler.get_name() == _HTTP_LOG_HANDLER_NAME for handler in logger.handlers
    ):
        handler = logging.StreamHandler()
        handler.set_name(_HTTP_LOG_HANDLER_NAME)
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    logger.disabled = False
    return logger


class RequestIDMiddleware:
    """Resolve and propagate one request ID for each HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.logger = logging.getLogger(HTTP_LOGGER_NAME)

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        started_at = monotonic()
        request_id_values = [
            value.decode("latin-1")
            for name, value in scope.get("headers", ())
            if name.lower() == _REQUEST_ID_HEADER_BYTES
        ]
        request_id = resolve_request_id(request_id_values)
        scope.setdefault("state", {})[REQUEST_ID_STATE_KEY] = request_id
        response_started = False
        started_status_code: int | None = None
        event_emitted = False

        async def send_with_request_id(message: Message) -> None:
            nonlocal response_started, started_status_code
            if message.get("type") == "http.response.start":
                status_code = int(message["status"])
                headers = [
                    (name, value)
                    for name, value in message.get("headers", ())
                    if name.lower() != _REQUEST_ID_HEADER_BYTES
                ]
                headers.append((_REQUEST_ID_HEADER_BYTES, request_id.encode("ascii")))
                message = {**message, "headers": headers}
                await send(message)
                response_started = True
                started_status_code = status_code
                return
            await send(message)

        def emit_event(status_code: int, error_category: ErrorCategory) -> None:
            nonlocal event_emitted
            if event_emitted:
                return
            method = scope.get("method", "UNKNOWN")
            event = HTTPRequestEvent(
                request_id=request_id,
                method=method if isinstance(method, str) else "UNKNOWN",
                route=classify_route(scope),
                status_code=status_code,
                duration_ms=(monotonic() - started_at) * 1000,
                error_category=error_category,
            )
            self.logger.info(
                json.dumps(
                    serialize_http_request_event(event),
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            event_emitted = True

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            if response_started:
                assert started_status_code is not None
                emit_event(started_status_code, ErrorCategory.STREAMING_ERROR)
                raise

            response = JSONResponse(
                {"detail": "Internal Server Error"},
                status_code=500,
            )
            await response(scope, receive, send_with_request_id)
            emit_event(500, ErrorCategory.UNHANDLED_EXCEPTION)
        else:
            if response_started:
                assert started_status_code is not None
                error_category = classify_http_status(started_status_code)
                state = scope.get("state")
                if isinstance(state, dict):
                    category_override = state.get(ERROR_CATEGORY_STATE_KEY)
                    if isinstance(category_override, ErrorCategory):
                        error_category = category_override
                emit_event(
                    started_status_code,
                    error_category,
                )
