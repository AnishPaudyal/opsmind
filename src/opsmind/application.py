"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.engine import Engine

from opsmind.api.dependencies import (
    get_clock,
    get_product_inventory_repository,
    get_recommendation_workflow_repository,
)
from opsmind.api.router import create_api_router
from opsmind.core.clock import Clock, SystemClock
from opsmind.core.config import PersistenceBackend, Settings, get_settings
from opsmind.persistence.postgresql.database import (
    create_postgresql_engine,
    create_session_factory,
    dispose_engine,
)
from opsmind.persistence.postgresql.repository import (
    PostgresProductInventoryRepository,
)
from opsmind.repositories.in_memory_recommendation_workflow import (
    InMemoryRecommendationWorkflowRepository,
)
from opsmind.repositories.memory import InMemoryProductInventoryRepository
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.repositories.recommendation_workflow import (
    RecommendationWorkflowRepository,
)


def create_app(
    settings: Settings | None = None,
    product_inventory_repository: ProductInventoryRepository | None = None,
    recommendation_workflow_repository: RecommendationWorkflowRepository | None = None,
    clock: Clock | None = None,
) -> FastAPI:
    """Create an OpsMind application with isolated settings and repositories."""
    resolved_settings = settings if settings is not None else get_settings()
    owned_engine: Engine | None = None
    resolved_repository: ProductInventoryRepository
    if product_inventory_repository is not None:
        resolved_repository = product_inventory_repository
    elif resolved_settings.persistence_backend is PersistenceBackend.MEMORY:
        resolved_repository = InMemoryProductInventoryRepository()
    else:
        if resolved_settings.database_url is None:
            raise RuntimeError("PostgreSQL database URL is not configured.")
        owned_engine = create_postgresql_engine(resolved_settings.database_url)
        resolved_repository = PostgresProductInventoryRepository(
            create_session_factory(owned_engine)
        )
    resolved_workflow_repository = (
        recommendation_workflow_repository
        if recommendation_workflow_repository is not None
        else InMemoryRecommendationWorkflowRepository()
    )
    resolved_clock = clock if clock is not None else SystemClock()

    def provide_settings() -> Settings:
        return resolved_settings

    def provide_product_inventory_repository() -> ProductInventoryRepository:
        return resolved_repository

    def provide_recommendation_workflow_repository() -> (
        RecommendationWorkflowRepository
    ):
        return resolved_workflow_repository

    def provide_clock() -> Clock:
        return resolved_clock

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if owned_engine is not None:
                dispose_engine(owned_engine)

    application = FastAPI(
        title=resolved_settings.application_name,
        description=f"{resolved_settings.service_name} API",
        debug=resolved_settings.debug,
        lifespan=lifespan,
    )
    application.dependency_overrides[get_settings] = provide_settings
    application.dependency_overrides[get_product_inventory_repository] = (
        provide_product_inventory_repository
    )
    application.dependency_overrides[get_recommendation_workflow_repository] = (
        provide_recommendation_workflow_repository
    )
    application.dependency_overrides[get_clock] = provide_clock
    application.include_router(create_api_router(resolved_settings.api_v1_prefix))
    return application
