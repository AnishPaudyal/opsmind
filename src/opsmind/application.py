"""FastAPI application factory."""

from fastapi import FastAPI

from opsmind.api.dependencies import get_product_inventory_repository
from opsmind.api.router import create_api_router
from opsmind.core.config import Settings, get_settings
from opsmind.repositories.memory import InMemoryProductInventoryRepository
from opsmind.repositories.product_inventory import ProductInventoryRepository


def create_app(
    settings: Settings | None = None,
    product_inventory_repository: ProductInventoryRepository | None = None,
) -> FastAPI:
    """Create an OpsMind application with isolated settings and repository."""
    resolved_settings = settings if settings is not None else get_settings()
    resolved_repository = (
        product_inventory_repository
        if product_inventory_repository is not None
        else InMemoryProductInventoryRepository()
    )

    def provide_settings() -> Settings:
        return resolved_settings

    def provide_product_inventory_repository() -> ProductInventoryRepository:
        return resolved_repository

    application = FastAPI(
        title=resolved_settings.application_name,
        description=f"{resolved_settings.service_name} API",
        debug=resolved_settings.debug,
    )
    application.dependency_overrides[get_settings] = provide_settings
    application.dependency_overrides[get_product_inventory_repository] = (
        provide_product_inventory_repository
    )
    application.include_router(create_api_router(resolved_settings.api_v1_prefix))
    return application
