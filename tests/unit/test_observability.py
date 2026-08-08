"""Tests for pure request-ID validation and resolution."""

import asyncio
from collections.abc import Sequence
from dataclasses import FrozenInstanceError
from typing import Any
from uuid import UUID

import pytest
from starlette.types import Message, Receive, Scope, Send

from opsmind.observability import (
    REQUEST_ID_HEADER,
    REQUEST_ID_STATE_KEY,
    ErrorCategory,
    HTTPRequestEvent,
    RequestIDMiddleware,
    classify_http_status,
    is_valid_request_id,
    resolve_request_id,
    serialize_http_request_event,
)


def assert_uuid4(value: str) -> None:
    """Assert that a value is a canonical UUID version 4 string."""
    parsed = UUID(value)

    assert parsed.version == 4
    assert str(parsed) == value


def invoke_http_middleware(
    request_headers: Sequence[tuple[bytes, bytes]] = (),
    response_headers: Sequence[tuple[bytes, bytes]] = (),
    state: dict[str, Any] | None = None,
) -> tuple[str, Scope, list[Message], Message]:
    """Run request-ID middleware around a minimal synthetic HTTP app."""
    scope: Scope = {
        "type": "http",
        "headers": list(request_headers),
    }
    if state is not None:
        scope["state"] = state

    downstream_request_id: str | None = None
    sent_messages: list[Message] = []
    body_message: Message = {
        "type": "http.response.body",
        "body": b"response body",
        "more_body": False,
    }

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del receive
        nonlocal downstream_request_id
        downstream_request_id = scope["state"][REQUEST_ID_STATE_KEY]
        await send(
            {
                "type": "http.response.start",
                "status": 201,
                "headers": list(response_headers),
            }
        )
        await send(body_message)

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent_messages.append(message)

    asyncio.run(RequestIDMiddleware(app)(scope, receive, send))
    assert downstream_request_id is not None
    return downstream_request_id, scope, sent_messages, body_message


def request_id_response_values(message: Message) -> list[bytes]:
    """Return every raw request-ID value from one response-start message."""
    return [
        value
        for name, value in message.get("headers", [])
        if name.lower() == b"x-request-id"
    ]


def test_request_id_header_uses_canonical_public_name() -> None:
    assert REQUEST_ID_HEADER == "X-Request-ID"


@pytest.mark.parametrize(
    "value",
    [
        "a",
        "Request123",
        "request-123",
        "request_123",
        "request.123",
        "a" * 64,
    ],
)
def test_valid_request_ids_are_accepted(value: str) -> None:
    assert is_valid_request_id(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "-request",
        "_request",
        ".request",
        " request-123",
        "request-123 ",
        "request/123",
        "request:123",
        "réquest",
        "a" * 65,
    ],
)
def test_invalid_request_ids_are_rejected(value: str) -> None:
    assert not is_valid_request_id(value)


def test_exactly_one_valid_caller_request_id_is_preserved() -> None:
    caller_request_id = "Caller.Request_ID-123"

    assert resolve_request_id([caller_request_id]) == caller_request_id


def test_absent_request_id_generates_uuid4() -> None:
    assert_uuid4(resolve_request_id([]))


def test_malformed_request_id_is_replaced_with_uuid4() -> None:
    generated = resolve_request_id([" request-123 "])

    assert generated != " request-123 "
    assert_uuid4(generated)


@pytest.mark.parametrize(
    "values",
    [
        ["request-123", "request-456"],
        ["request-123", "request-123"],
    ],
)
def test_duplicate_request_ids_are_replaced_with_uuid4(values: list[str]) -> None:
    generated = resolve_request_id(values)

    assert generated not in values
    assert_uuid4(generated)


def test_absent_request_id_reaches_state_and_response_as_same_uuid4() -> None:
    downstream_request_id, scope, messages, _ = invoke_http_middleware()

    assert_uuid4(downstream_request_id)
    assert scope["state"][REQUEST_ID_STATE_KEY] == downstream_request_id
    assert request_id_response_values(messages[0]) == [
        downstream_request_id.encode("ascii")
    ]


def test_one_valid_raw_request_id_is_preserved_in_state_and_response() -> None:
    downstream_request_id, _, messages, _ = invoke_http_middleware(
        [(b"X-Request-ID", b"Caller.Request_ID-123")]
    )

    assert downstream_request_id == "Caller.Request_ID-123"
    assert request_id_response_values(messages[0]) == [b"Caller.Request_ID-123"]


def test_malformed_raw_request_id_is_replaced_without_crashing() -> None:
    downstream_request_id, _, messages, _ = invoke_http_middleware(
        [(b"x-request-id", b"invalid/value\xff")]
    )

    assert downstream_request_id != "invalid/value\xff"
    assert_uuid4(downstream_request_id)
    assert request_id_response_values(messages[0]) == [
        downstream_request_id.encode("ascii")
    ]


def test_identical_duplicate_raw_request_ids_are_replaced() -> None:
    downstream_request_id, _, messages, _ = invoke_http_middleware(
        [
            (b"x-request-id", b"caller-123"),
            (b"X-REQUEST-ID", b"caller-123"),
        ]
    )

    assert downstream_request_id != "caller-123"
    assert_uuid4(downstream_request_id)
    assert request_id_response_values(messages[0]) == [
        downstream_request_id.encode("ascii")
    ]


def test_middleware_owns_one_response_header_and_preserves_unrelated_headers() -> None:
    downstream_request_id, _, messages, _ = invoke_http_middleware(
        [(b"x-request-id", b"caller-123")],
        [
            (b"content-type", b"text/plain"),
            (b"x-request-id", b"downstream-one"),
            (b"X-Request-ID", b"downstream-two"),
            (b"set-cookie", b"session=synthetic"),
        ],
    )

    response_start = messages[0]
    assert response_start["status"] == 201
    assert request_id_response_values(response_start) == [b"caller-123"]
    assert (b"content-type", b"text/plain") in response_start["headers"]
    assert (b"set-cookie", b"session=synthetic") in response_start["headers"]
    assert downstream_request_id == "caller-123"


def test_existing_state_and_body_message_are_preserved() -> None:
    existing_state = {"existing": "preserved"}

    downstream_request_id, scope, messages, body_message = invoke_http_middleware(
        state=existing_state
    )

    assert scope["state"] is existing_state
    assert existing_state == {
        "existing": "preserved",
        REQUEST_ID_STATE_KEY: downstream_request_id,
    }
    assert messages[1] is body_message
    assert messages[1] == {
        "type": "http.response.body",
        "body": b"response body",
        "more_body": False,
    }


def test_non_http_scope_passes_through_without_mutation() -> None:
    existing_state = {"existing": "preserved"}
    scope: Scope = {"type": "websocket", "state": existing_state}
    sent_messages: list[Message] = []
    downstream_message: Message = {
        "type": "websocket.accept",
        "headers": [(b"x-request-id", b"downstream")],
    }
    downstream_scope: Scope | None = None

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del receive
        nonlocal downstream_scope
        downstream_scope = scope
        await send(downstream_message)

    async def receive() -> Message:
        return {"type": "websocket.disconnect", "code": 1000}

    async def send(message: Message) -> None:
        sent_messages.append(message)

    asyncio.run(RequestIDMiddleware(app)(scope, receive, send))

    assert downstream_scope is scope
    assert scope["state"] is existing_state
    assert existing_state == {"existing": "preserved"}
    assert sent_messages == [downstream_message]
    assert sent_messages[0] is downstream_message


def test_error_categories_are_exactly_the_governed_vocabulary() -> None:
    assert [category.value for category in ErrorCategory] == [
        "none",
        "client_error",
        "dependency_unavailable",
        "server_error",
        "unhandled_exception",
        "streaming_error",
    ]


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (200, ErrorCategory.NONE),
        (399, ErrorCategory.NONE),
        (400, ErrorCategory.CLIENT_ERROR),
        (404, ErrorCategory.CLIENT_ERROR),
        (499, ErrorCategory.CLIENT_ERROR),
        (500, ErrorCategory.SERVER_ERROR),
        (503, ErrorCategory.SERVER_ERROR),
        (599, ErrorCategory.SERVER_ERROR),
    ],
)
def test_completed_http_status_uses_generic_bounded_category(
    status_code: int,
    expected: ErrorCategory,
) -> None:
    assert classify_http_status(status_code) is expected


def test_http_request_event_preserves_governed_values() -> None:
    event = HTTPRequestEvent(
        request_id="request-123",
        method="GET",
        route="/api/v1/products/{product_id}",
        status_code=404,
        duration_ms=12.345,
        error_category=ErrorCategory.CLIENT_ERROR,
    )

    assert event.event == "http_request"
    assert event.request_id == "request-123"
    assert event.method == "GET"
    assert event.route == "/api/v1/products/{product_id}"
    assert event.status_code == 404
    assert event.duration_ms == 12.345
    assert event.error_category is ErrorCategory.CLIENT_ERROR
    with pytest.raises(FrozenInstanceError):
        event.status_code = 200  # type: ignore[misc]


def test_http_request_event_serialization_contains_only_governed_fields() -> None:
    event = HTTPRequestEvent(
        request_id="request-123",
        method="POST",
        route="/api/v1/products/{product_id}",
        status_code=503,
        duration_ms=7.5,
        error_category=ErrorCategory.DEPENDENCY_UNAVAILABLE,
    )

    assert serialize_http_request_event(event) == {
        "event": "http_request",
        "request_id": "request-123",
        "method": "POST",
        "route": "/api/v1/products/{product_id}",
        "status_code": 503,
        "duration_ms": 7.5,
        "error_category": "dependency_unavailable",
    }
