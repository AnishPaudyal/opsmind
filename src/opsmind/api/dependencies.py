"""FastAPI dependencies for application-bound services."""

from opsmind.core.clock import Clock
from opsmind.readiness import ReadinessProbe
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.repositories.recommendation_workflow import (
    RecommendationWorkflowRepository,
)


def get_product_inventory_repository() -> ProductInventoryRepository:
    """Return the application-bound product and inventory repository."""
    raise RuntimeError("Product inventory repository is not configured")


def get_recommendation_workflow_repository() -> RecommendationWorkflowRepository:
    """Return the application-bound recommendation workflow repository."""
    raise RuntimeError("Recommendation workflow repository is not configured")


def get_clock() -> Clock:
    """Return the application-bound workflow clock."""
    raise RuntimeError("Clock is not configured")


def get_readiness_probe() -> ReadinessProbe:
    """Return the application-bound readiness probe."""
    raise RuntimeError("Readiness probe is not configured")
