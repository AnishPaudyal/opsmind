"""FastAPI dependencies for product and inventory operations."""

from opsmind.repositories.product_inventory import ProductInventoryRepository


def get_product_inventory_repository() -> ProductInventoryRepository:
    """Return the application-bound product and inventory repository."""
    raise RuntimeError("Product inventory repository is not configured")
