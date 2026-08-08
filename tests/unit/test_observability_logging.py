"""Tests for bounded structured HTTP request logging."""

import asyncio
import json
import logging
from collections.abc import Iterator
from types import SimpleNamespace

import pytest
from starlette.types import Message, Receive, Scope, Send

import opsmind.observability as observability_module
from opsmind.observability import (
    HTTP_LOGGER_NAME,
    REQUEST_ID_HEADER,
    REQUEST_ID_STATE_KEY,
    RequestIDMiddleware,
    classify_route,
    configure_http_logger,
)


class RecordingHandler(logging.Handler):
    """Capture formatted log messages without changing the root logger."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


class SyntheticControlFlow(BaseException):
    """Safe BaseException subtype for verifying the catch boundary."""


@pytest.fixture
def isolated_http_logger() -> Iterator[logging.Logger]:
    """Isolate the dedicated logger and restore its process-global state."""
    logger = logging.getLogger(HTTP_LOGGER_NAME)
    previous_handlers = list(logger.handlers)
    previous_level = logger.level
    previous_propagate = logger.propagate
    previous_disabled = logger.disabled
    logger.handlers.clear()
    logger.setLevel(logging.NOTSET)
    logger.propagate = True
    logger.disabled = False
    try:
        yield logger
    finally:
        for handler in logger.handlers:
            if handler not in previous_handlers:
                handler.close()
        logger.handlers[:] = previous_handlers
        logger.setLevel(previous_level)
        logger.propagate = previous_propagate
        logger.disabled = previous_disabled


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        (
            {
                "type": "http",
                "router": object(),
                "fastapi": {
                    "effective_route_context": SimpleNamespace(
                        path_format="/api/v1/products/{product_id}"
                    )
                },
                "route": SimpleNamespace(path_format="/products/{product_id}"),
            },
            "/api/v1/products/{product_id}",
        ),
        ({"type": "http", "router": object()}, "unmatched"),
        ({"type": "http"}, "unknown"),
    ],
)
def test_route_classification_uses_only_post_routing_metadata(
    scope: Scope,
    expected: str,
) -> None:
    assert classify_route(scope) == expected


def test_middleware_emits_one_exact_safe_event_with_monotonic_duration(
    monkeypatch: pytest.MonkeyPatch,
    isolated_http_logger: logging.Logger,
) -> None:
    current_time = [100.0]
    monkeypatch.setattr(observability_module, "monotonic", lambda: current_time[0])
    recorder = RecordingHandler()
    isolated_http_logger.addHandler(recorder)
    isolated_http_logger.setLevel(logging.INFO)
    isolated_http_logger.propagate = False

    concrete_id = "123e4567-e89b-12d3-a456-426614174000"
    query_secret = "secret-query-value"
    auth_secret = "secret-auth-value"
    header_secret = "secret-header-value"
    body_secret = "secret-recommendation-note"
    scope: Scope = {
        "type": "http",
        "method": "POST",
        "path": f"/api/v1/products/{concrete_id}",
        "query_string": f"token={query_secret}".encode("ascii"),
        "headers": [
            (b"x-request-id", b"caller-123"),
            (b"authorization", f"Bearer {auth_secret}".encode("ascii")),
            (b"x-synthetic-secret", header_secret.encode("ascii")),
        ],
        "router": object(),
        "route": SimpleNamespace(path_format="/api/v1/products/{product_id}"),
    }
    sent_messages: list[Message] = []
    downstream_request_id: str | None = None

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        nonlocal downstream_request_id
        downstream_request_id = scope["state"][REQUEST_ID_STATE_KEY]
        request_message = await receive()
        assert request_message["body"] == body_secret.encode("ascii")
        await send(
            {
                "type": "http.response.start",
                "status": 201,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        current_time[0] = 100.0125
        await send(
            {
                "type": "http.response.body",
                "body": b'{"created":true}',
                "more_body": False,
            }
        )

    async def receive() -> Message:
        return {
            "type": "http.request",
            "body": body_secret.encode("ascii"),
            "more_body": False,
        }

    async def send(message: Message) -> None:
        sent_messages.append(message)

    asyncio.run(RequestIDMiddleware(app)(scope, receive, send))

    assert len(recorder.messages) == 1
    log_message = recorder.messages[0]
    payload = json.loads(log_message)
    assert set(payload) == {
        "event",
        "request_id",
        "method",
        "route",
        "status_code",
        "duration_ms",
        "error_category",
    }
    assert payload == {
        "event": "http_request",
        "request_id": "caller-123",
        "method": "POST",
        "route": "/api/v1/products/{product_id}",
        "status_code": 201,
        "duration_ms": pytest.approx(12.5),
        "error_category": "none",
    }
    assert payload["duration_ms"] >= 0
    assert downstream_request_id == "caller-123"
    assert [
        value
        for name, value in sent_messages[0]["headers"]
        if name.lower() == REQUEST_ID_HEADER.lower().encode("ascii")
    ] == [b"caller-123"]
    for excluded in (
        concrete_id,
        query_secret,
        auth_secret,
        header_secret,
        body_secret,
    ):
        assert excluded not in log_message


def test_http_logger_configuration_is_idempotent(
    isolated_http_logger: logging.Logger,
) -> None:
    isolated_http_logger.disabled = True

    first = configure_http_logger()
    initial_handlers = list(first.handlers)

    second = configure_http_logger()
    third = configure_http_logger()

    assert first is isolated_http_logger
    assert second is first
    assert third is first
    assert first.handlers == initial_handlers
    assert len(first.handlers) == 1
    assert first.level == logging.INFO
    assert first.propagate is False
    assert first.disabled is False


def test_pre_response_exception_returns_safe_500_and_one_bounded_event(
    monkeypatch: pytest.MonkeyPatch,
    isolated_http_logger: logging.Logger,
) -> None:
    current_time = [200.0]
    monkeypatch.setattr(observability_module, "monotonic", lambda: current_time[0])
    recorder = RecordingHandler()
    isolated_http_logger.addHandler(recorder)
    isolated_http_logger.setLevel(logging.INFO)
    isolated_http_logger.propagate = False
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "headers": [(b"x-request-id", b"caller-123")],
    }
    sent_messages: list[Message] = []
    secret = "super-secret-internal-detail"

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del scope, receive, send
        current_time[0] = 200.02
        raise RuntimeError(secret)

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent_messages.append(message)
        if message["type"] == "http.response.body":
            current_time[0] = 200.03

    asyncio.run(RequestIDMiddleware(app)(scope, receive, send))

    response_start, response_body = sent_messages
    assert response_start["type"] == "http.response.start"
    assert response_start["status"] == 500
    assert [
        value
        for name, value in response_start["headers"]
        if name.lower() == b"x-request-id"
    ] == [b"caller-123"]
    assert response_body == {
        "type": "http.response.body",
        "body": b'{"detail":"Internal Server Error"}',
    }
    assert secret not in response_body["body"].decode("utf-8")
    assert scope["state"][REQUEST_ID_STATE_KEY] == "caller-123"
    assert len(recorder.messages) == 1
    payload = json.loads(recorder.messages[0])
    assert payload["request_id"] == "caller-123"
    assert payload["route"] == "unknown"
    assert payload["status_code"] == 500
    assert payload["duration_ms"] == pytest.approx(30.0)
    assert payload["error_category"] == "unhandled_exception"
    assert secret not in recorder.messages[0]
    assert "Traceback" not in recorder.messages[0]


def test_post_response_exception_emits_one_streaming_error_and_reraises(
    monkeypatch: pytest.MonkeyPatch,
    isolated_http_logger: logging.Logger,
) -> None:
    current_time = [300.0]
    monkeypatch.setattr(observability_module, "monotonic", lambda: current_time[0])
    recorder = RecordingHandler()
    isolated_http_logger.addHandler(recorder)
    isolated_http_logger.setLevel(logging.INFO)
    isolated_http_logger.propagate = False
    scope: Scope = {
        "type": "http",
        "method": "GET",
        "headers": [(b"x-request-id", b"caller-123")],
        "router": object(),
        "route": SimpleNamespace(path_format="/stream"),
    }
    sent_messages: list[Message] = []
    secret = "stream-secret"

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del scope, receive
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"partial",
                "more_body": True,
            }
        )
        current_time[0] = 300.025
        raise RuntimeError(secret)

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent_messages.append(message)

    with pytest.raises(RuntimeError, match=secret):
        asyncio.run(RequestIDMiddleware(app)(scope, receive, send))

    assert [message["type"] for message in sent_messages] == [
        "http.response.start",
        "http.response.body",
    ]
    assert sent_messages[0]["status"] == 200
    assert len(recorder.messages) == 1
    payload = json.loads(recorder.messages[0])
    assert payload["request_id"] == "caller-123"
    assert payload["route"] == "/stream"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == pytest.approx(25.0)
    assert payload["error_category"] == "streaming_error"
    assert secret not in recorder.messages[0]


def test_base_exception_is_not_converted_to_safe_500(
    isolated_http_logger: logging.Logger,
) -> None:
    recorder = RecordingHandler()
    isolated_http_logger.addHandler(recorder)
    isolated_http_logger.setLevel(logging.INFO)
    isolated_http_logger.propagate = False
    scope: Scope = {"type": "http", "method": "GET", "headers": []}
    sent_messages: list[Message] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        del scope, receive, send
        raise SyntheticControlFlow

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent_messages.append(message)

    with pytest.raises(SyntheticControlFlow):
        asyncio.run(RequestIDMiddleware(app)(scope, receive, send))

    assert sent_messages == []
    assert recorder.messages == []
