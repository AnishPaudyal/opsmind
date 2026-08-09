"""Tests for FastAPI application construction."""

import json
import logging
import os
from importlib import import_module
from typing import Protocol, cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx2 import Response
from pydantic import SecretStr
from sqlalchemy.engine import Engine

import opsmind.application as application_module
import opsmind.persistence.postgresql.database as postgresql_database
from opsmind.api.dependencies import (
    get_authenticator,
    get_clock,
    get_product_inventory_repository,
    get_readiness_probe,
    get_recommendation_workflow_repository,
)
from opsmind.application import create_app
from opsmind.core.clock import SystemClock
from opsmind.core.config import (
    Environment,
    PersistenceBackend,
    Settings,
    get_settings,
    reset_settings_cache,
)
from opsmind.observability import HTTP_LOGGER_NAME, REQUEST_ID_HEADER
from opsmind.persistence.postgresql.database import SessionFactory
from opsmind.persistence.postgresql.repository import (
    PostgresProductInventoryRepository,
)
from opsmind.persistence.postgresql.workflow_repository import (
    PostgresRecommendationWorkflowRepository,
)
from opsmind.readiness import (
    MemoryReadinessProbe,
    PostgreSQLReadinessProbe,
)
from opsmind.repositories.in_memory_recommendation_workflow import (
    InMemoryRecommendationWorkflowRepository,
)
from opsmind.repositories.memory import InMemoryProductInventoryRepository
from tests.security import authenticated_test_client, create_authenticated_test_app


class ApplicationModule(Protocol):
    """Typed view of the ASGI entry-point module."""

    app: FastAPI


def create_request_id_test_client() -> TestClient:
    """Create a real application client with deterministic settings."""
    settings = Settings(
        application_name="OpsMind Test",
        service_name="opsmind-test-api",
        environment=Environment.TEST,
        api_v1_prefix="/api/v1",
    )
    return authenticated_test_client(create_authenticated_test_app(settings))


def assert_single_uuid4_request_id(response: Response) -> None:
    """Assert one canonical generated request-ID response header."""
    request_id_values = response.headers.get_list(REQUEST_ID_HEADER)

    assert len(request_id_values) == 1
    request_id = request_id_values[0]
    parsed = UUID(request_id)
    assert parsed.version == 4
    assert str(parsed) == request_id


def test_create_app_uses_supplied_settings_for_metadata() -> None:
    settings = Settings(
        application_name="OpsMind Test",
        service_name="opsmind-test-api",
        environment=Environment.TEST,
        debug=True,
        api_v1_prefix="/api/v1",
    )

    application = create_app(settings)

    assert isinstance(application, FastAPI)
    assert application.title == "OpsMind Test"
    assert application.description == "opsmind-test-api API"
    assert application.debug is True


def test_request_id_surrounds_successful_health_without_changing_contract() -> None:
    response = create_request_id_test_client().get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "opsmind-test-api",
        "environment": "test",
    }
    assert_single_uuid4_request_id(response)


def test_valid_caller_request_id_is_propagated_by_real_application() -> None:
    response = create_request_id_test_client().get(
        "/health",
        headers={REQUEST_ID_HEADER: "caller-123"},
    )

    assert response.status_code == 200
    assert response.headers.get_list(REQUEST_ID_HEADER) == ["caller-123"]


def test_handled_product_404_keeps_body_and_gains_request_id() -> None:
    missing_product_id = "00000000-0000-0000-0000-000000000099"

    response = create_request_id_test_client().get(
        f"/api/v1/products/{missing_product_id}"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Product '{missing_product_id}' was not found."
    }
    assert_single_uuid4_request_id(response)


def test_fastapi_validation_422_keeps_payload_and_gains_request_id() -> None:
    response = create_request_id_test_client().get("/api/v1/products/not-a-uuid")

    assert response.status_code == 422
    assert response.json() == {
        "detail": [
            {
                "type": "uuid_parsing",
                "loc": ["path", "product_id"],
                "msg": "Input should be a valid UUID, invalid character: found `n` at 1",
                "input": "not-a-uuid",
                "ctx": {"error": "invalid character: found `n` at 1"},
            }
        ]
    }
    assert_single_uuid4_request_id(response)


def test_unmatched_route_404_keeps_payload_and_gains_request_id() -> None:
    response = create_request_id_test_client().get("/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}
    assert_single_uuid4_request_id(response)


@pytest.mark.parametrize(
    ("path", "expected_route", "expected_status", "expected_category"),
    [
        ("/health", "/health", 200, "none"),
        (
            "/api/v1/products/00000000-0000-0000-0000-000000000099",
            "/api/v1/products/{product_id}",
            404,
            "client_error",
        ),
        (
            "/api/v1/products/not-a-uuid",
            "/api/v1/products/{product_id}",
            422,
            "client_error",
        ),
        ("/does-not-exist", "unmatched", 404, "client_error"),
    ],
)
def test_structured_event_uses_real_fastapi_route_classification(
    path: str,
    expected_route: str,
    expected_status: int,
    expected_category: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = create_request_id_test_client()
    emitted_messages: list[str] = []

    def record_message(message: object, *args: object, **kwargs: object) -> None:
        del args, kwargs
        emitted_messages.append(str(message))

    monkeypatch.setattr(
        logging.getLogger(HTTP_LOGGER_NAME),
        "info",
        record_message,
    )

    response = client.get(path, headers={REQUEST_ID_HEADER: "caller-123"})

    assert response.status_code == expected_status
    assert len(emitted_messages) == 1
    payload = json.loads(emitted_messages[0])
    assert payload["request_id"] == response.headers[REQUEST_ID_HEADER]
    assert payload["method"] == "GET"
    assert payload["route"] == expected_route
    assert payload["status_code"] == expected_status
    assert payload["error_category"] == expected_category
    assert isinstance(payload["duration_ms"], int | float)
    assert payload["duration_ms"] >= 0


def test_real_application_unexpected_exception_returns_safe_correlated_500(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "repository-password=super-secret"
    repository = InMemoryProductInventoryRepository()

    def raise_unexpectedly(_: UUID) -> None:
        raise RuntimeError(secret)

    monkeypatch.setattr(repository, "get_product", raise_unexpectedly)
    settings = Settings(environment=Environment.TEST, api_v1_prefix="/api/v1")
    client = authenticated_test_client(
        create_authenticated_test_app(
            settings,
            product_inventory_repository=repository,
        )
    )
    emitted_messages: list[str] = []

    def record_message(message: object, *args: object, **kwargs: object) -> None:
        del args, kwargs
        emitted_messages.append(str(message))

    monkeypatch.setattr(
        logging.getLogger(HTTP_LOGGER_NAME),
        "info",
        record_message,
    )

    response = client.get(
        "/api/v1/products/00000000-0000-0000-0000-000000000001",
        headers={REQUEST_ID_HEADER: "caller-123"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal Server Error"}
    assert response.headers.get_list(REQUEST_ID_HEADER) == ["caller-123"]
    assert secret not in response.text
    assert len(emitted_messages) == 1
    payload = json.loads(emitted_messages[0])
    assert payload["request_id"] == "caller-123"
    assert payload["route"] == "/api/v1/products/{product_id}"
    assert payload["status_code"] == 500
    assert payload["error_category"] == "unhandled_exception"
    assert secret not in emitted_messages[0]


def test_create_app_provides_the_same_settings_instance() -> None:
    settings = Settings(environment=Environment.TEST)
    application = create_app(settings)

    settings_provider = application.dependency_overrides[get_settings]

    assert settings_provider() is settings


def test_root_router_keeps_health_unversioned_without_an_empty_version_route() -> None:
    settings = Settings(environment=Environment.TEST, api_v1_prefix="/api/v1")
    application = create_app(settings)
    route_paths = set(cast(dict[str, object], application.openapi()["paths"]))

    assert "/health" in route_paths
    assert settings.api_v1_prefix not in route_paths
    assert f"{settings.api_v1_prefix}/products" in route_paths


def test_memory_backend_selects_both_default_repositories() -> None:
    settings = Settings(environment=Environment.TEST)

    application = create_app(settings)

    product_provider = application.dependency_overrides[
        get_product_inventory_repository
    ]
    workflow_provider = application.dependency_overrides[
        get_recommendation_workflow_repository
    ]
    readiness_provider = application.dependency_overrides[get_readiness_probe]

    assert isinstance(
        product_provider(),
        InMemoryProductInventoryRepository,
    )
    assert isinstance(
        workflow_provider(),
        InMemoryRecommendationWorkflowRepository,
    )
    assert isinstance(readiness_provider(), MemoryReadinessProbe)


def test_memory_applications_receive_separate_readiness_probes() -> None:
    settings = Settings(environment=Environment.TEST)
    first = create_app(settings)
    second = create_app(settings)

    first_provider = first.dependency_overrides[get_readiness_probe]
    second_provider = second.dependency_overrides[get_readiness_probe]

    assert first_provider() is not second_provider()


def test_create_app_provides_the_supplied_repository_instance() -> None:
    settings = Settings(environment=Environment.TEST)
    repository = InMemoryProductInventoryRepository()
    application = create_app(settings, repository)

    repository_provider = application.dependency_overrides[
        get_product_inventory_repository
    ]

    assert repository_provider() is repository


def test_explicit_repositories_precede_postgresql_backend_selection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        environment=Environment.TEST,
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(
            "postgresql+psycopg://opsmind:secret@127.0.0.1:1/opsmind"
        ),
    )
    product_repository = InMemoryProductInventoryRepository()
    workflow_repository = InMemoryRecommendationWorkflowRepository()

    def unexpected_engine_creation(_: object) -> Engine:
        raise AssertionError("explicit injection must not create an engine")

    def unexpected_engine_disposal(_: Engine) -> None:
        raise AssertionError("externally supplied repositories own their resources")

    monkeypatch.setattr(
        application_module,
        "create_postgresql_engine",
        unexpected_engine_creation,
    )
    monkeypatch.setattr(
        application_module,
        "dispose_engine",
        unexpected_engine_disposal,
    )

    application = create_app(
        settings,
        product_repository,
        workflow_repository,
        readiness_probe=MemoryReadinessProbe(),
    )

    product_provider = application.dependency_overrides[
        get_product_inventory_repository
    ]
    workflow_provider = application.dependency_overrides[
        get_recommendation_workflow_repository
    ]

    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert product_provider() is product_repository
        assert workflow_provider() is workflow_repository


def test_explicit_postgresql_repositories_require_explicit_readiness() -> None:
    settings = Settings(
        environment=Environment.TEST,
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(
            "postgresql+psycopg://opsmind:secret@127.0.0.1:1/opsmind"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=r"^A readiness probe is required when PostgreSQL repositories ",
    ):
        create_app(
            settings,
            InMemoryProductInventoryRepository(),
            InMemoryRecommendationWorkflowRepository(),
        )


def test_postgresql_backend_selects_both_repositories_with_shared_factory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        environment=Environment.TEST,
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(
            "postgresql+psycopg://opsmind:secret@127.0.0.1:1/opsmind"
        ),
    )
    created_engines: list[Engine] = []
    created_session_factories: list[SessionFactory] = []
    product_session_factories: list[SessionFactory] = []
    workflow_session_factories: list[SessionFactory] = []
    disposed_engines: list[Engine] = []
    readiness_engines: list[Engine] = []

    original_create_engine = postgresql_database.create_postgresql_engine
    original_create_session_factory = postgresql_database.create_session_factory

    def tracked_engine_creation(database_url: SecretStr) -> Engine:
        engine = original_create_engine(database_url)
        created_engines.append(engine)
        return engine

    def tracked_session_factory_creation(
        engine: Engine,
    ) -> SessionFactory:
        session_factory = original_create_session_factory(engine)
        created_session_factories.append(session_factory)
        return session_factory

    def tracked_product_repository(
        session_factory: SessionFactory,
    ) -> PostgresProductInventoryRepository:
        product_session_factories.append(session_factory)
        return PostgresProductInventoryRepository(session_factory)

    def tracked_workflow_repository(
        session_factory: SessionFactory,
    ) -> PostgresRecommendationWorkflowRepository:
        workflow_session_factories.append(session_factory)
        return PostgresRecommendationWorkflowRepository(session_factory)

    def tracked_readiness_probe(engine: Engine) -> PostgreSQLReadinessProbe:
        readiness_engines.append(engine)
        return PostgreSQLReadinessProbe(engine)

    monkeypatch.setattr(
        application_module,
        "create_postgresql_engine",
        tracked_engine_creation,
    )
    monkeypatch.setattr(
        application_module,
        "create_session_factory",
        tracked_session_factory_creation,
    )
    monkeypatch.setattr(
        application_module,
        "PostgresProductInventoryRepository",
        tracked_product_repository,
    )
    monkeypatch.setattr(
        application_module,
        "PostgresRecommendationWorkflowRepository",
        tracked_workflow_repository,
    )
    monkeypatch.setattr(
        application_module,
        "PostgreSQLReadinessProbe",
        tracked_readiness_probe,
    )
    monkeypatch.setattr(
        application_module,
        "dispose_engine",
        disposed_engines.append,
    )

    application = create_app(settings)
    product_provider = application.dependency_overrides[
        get_product_inventory_repository
    ]
    workflow_provider = application.dependency_overrides[
        get_recommendation_workflow_repository
    ]

    with TestClient(application) as client:
        assert client.get("/health").status_code == 200

        product_repository = product_provider()
        workflow_repository = workflow_provider()

        assert isinstance(
            product_repository,
            PostgresProductInventoryRepository,
        )
        assert isinstance(
            workflow_repository,
            PostgresRecommendationWorkflowRepository,
        )
        assert len(created_engines) == 1
        assert len(created_session_factories) == 1
        assert product_session_factories == created_session_factories
        assert workflow_session_factories == created_session_factories
        assert readiness_engines == created_engines
        readiness_provider = application.dependency_overrides[get_readiness_probe]
        assert isinstance(readiness_provider(), PostgreSQLReadinessProbe)

    assert disposed_engines == created_engines
    created_engines[0].dispose()


def test_explicit_product_repository_creates_only_postgresql_workflow_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        environment=Environment.TEST,
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(
            "postgresql+psycopg://opsmind:secret@127.0.0.1:1/opsmind"
        ),
    )
    product_repository = InMemoryProductInventoryRepository()
    workflow_session_factories: list[SessionFactory] = []
    disposed_engines: list[Engine] = []

    def unexpected_product_default(
        _: SessionFactory,
    ) -> PostgresProductInventoryRepository:
        raise AssertionError(
            "explicit product injection must prevent product default creation"
        )

    def tracked_workflow_default(
        session_factory: SessionFactory,
    ) -> PostgresRecommendationWorkflowRepository:
        workflow_session_factories.append(session_factory)
        return PostgresRecommendationWorkflowRepository(session_factory)

    monkeypatch.setattr(
        application_module,
        "PostgresProductInventoryRepository",
        unexpected_product_default,
    )
    monkeypatch.setattr(
        application_module,
        "PostgresRecommendationWorkflowRepository",
        tracked_workflow_default,
    )
    monkeypatch.setattr(
        application_module,
        "dispose_engine",
        disposed_engines.append,
    )

    application = create_app(
        settings,
        product_inventory_repository=product_repository,
    )
    product_provider = application.dependency_overrides[
        get_product_inventory_repository
    ]
    workflow_provider = application.dependency_overrides[
        get_recommendation_workflow_repository
    ]

    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert product_provider() is product_repository
        assert isinstance(
            workflow_provider(),
            PostgresRecommendationWorkflowRepository,
        )

    assert len(workflow_session_factories) == 1
    assert len(disposed_engines) == 1
    disposed_engines[0].dispose()


def test_explicit_workflow_repository_creates_only_postgresql_product_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings(
        environment=Environment.TEST,
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(
            "postgresql+psycopg://opsmind:secret@127.0.0.1:1/opsmind"
        ),
    )
    workflow_repository = InMemoryRecommendationWorkflowRepository()
    product_session_factories: list[SessionFactory] = []
    disposed_engines: list[Engine] = []

    def tracked_product_default(
        session_factory: SessionFactory,
    ) -> PostgresProductInventoryRepository:
        product_session_factories.append(session_factory)
        return PostgresProductInventoryRepository(session_factory)

    def unexpected_workflow_default(
        _: SessionFactory,
    ) -> PostgresRecommendationWorkflowRepository:
        raise AssertionError(
            "explicit workflow injection must prevent workflow default creation"
        )

    monkeypatch.setattr(
        application_module,
        "PostgresProductInventoryRepository",
        tracked_product_default,
    )
    monkeypatch.setattr(
        application_module,
        "PostgresRecommendationWorkflowRepository",
        unexpected_workflow_default,
    )
    monkeypatch.setattr(
        application_module,
        "dispose_engine",
        disposed_engines.append,
    )

    application = create_app(
        settings,
        recommendation_workflow_repository=workflow_repository,
    )
    product_provider = application.dependency_overrides[
        get_product_inventory_repository
    ]
    workflow_provider = application.dependency_overrides[
        get_recommendation_workflow_repository
    ]

    with TestClient(application) as client:
        assert client.get("/health").status_code == 200
        assert isinstance(
            product_provider(),
            PostgresProductInventoryRepository,
        )
        assert workflow_provider() is workflow_repository

    assert len(product_session_factories) == 1
    assert len(disposed_engines) == 1
    disposed_engines[0].dispose()


def test_unbound_repository_dependency_fails_fast() -> None:
    with pytest.raises(
        RuntimeError,
        match=r"^Product inventory repository is not configured$",
    ):
        get_product_inventory_repository()


def test_create_app_provides_supplied_workflow_repository_and_clock() -> None:
    settings = Settings(environment=Environment.TEST)
    product_repository = InMemoryProductInventoryRepository()
    workflow_repository = InMemoryRecommendationWorkflowRepository()
    clock = SystemClock()
    application = create_app(
        settings,
        product_repository,
        workflow_repository,
        clock,
    )

    workflow_provider = application.dependency_overrides[
        get_recommendation_workflow_repository
    ]
    clock_provider = application.dependency_overrides[get_clock]

    assert workflow_provider() is workflow_repository
    assert clock_provider() is clock


def test_unbound_workflow_dependencies_fail_fast() -> None:
    with pytest.raises(
        RuntimeError,
        match=r"^Recommendation workflow repository is not configured$",
    ):
        get_recommendation_workflow_repository()


def test_unbound_authenticator_dependency_fails_fast() -> None:
    with pytest.raises(RuntimeError, match=r"^Authenticator is not configured$"):
        get_authenticator()
    with pytest.raises(RuntimeError, match=r"^Clock is not configured$"):
        get_clock()
    with pytest.raises(RuntimeError, match=r"^Readiness probe is not configured$"):
        get_readiness_probe()


def test_main_exposes_the_default_asgi_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable_name in tuple(os.environ):
        if variable_name.startswith("OPSMIND_"):
            monkeypatch.delenv(variable_name, raising=False)
    reset_settings_cache()

    main_module = cast(ApplicationModule, import_module("opsmind.main"))

    assert isinstance(main_module.app, FastAPI)
    assert main_module.app.title == "OpsMind"

    reset_settings_cache()
