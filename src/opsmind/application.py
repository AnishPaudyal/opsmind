"""FastAPI application factory."""

from fastapi import FastAPI

from opsmind.api.dependencies import (
    get_clock,
    get_product_inventory_repository,
    get_recommendation_workflow_repository,
)
from opsmind.api.router import create_api_router
from opsmind.core.clock import Clock, SystemClock
from opsmind.core.config import Settings, get_settings
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
    resolved_repository = (
        product_inventory_repository
        if product_inventory_repository is not None
        else InMemoryProductInventoryRepository()
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

    application = FastAPI(
        title=resolved_settings.application_name,
        description=f"{resolved_settings.service_name} API",
        debug=resolved_settings.debug,
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
