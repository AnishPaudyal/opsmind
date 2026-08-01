"""Top-level API router composition."""

from fastapi import APIRouter

from opsmind.api.routes.demand import router as demand_router
from opsmind.api.routes.forecast import router as forecast_router
from opsmind.api.routes.health import router as health_router
from opsmind.api.routes.products import router as products_router


def create_api_router(api_v1_prefix: str) -> APIRouter:
    """Compose unversioned process routes and versioned business routes."""
    api_router = APIRouter()
    api_router.include_router(health_router)
    api_router.include_router(products_router, prefix=api_v1_prefix)
    api_router.include_router(demand_router, prefix=api_v1_prefix)
    api_router.include_router(forecast_router, prefix=api_v1_prefix)
    return api_router
