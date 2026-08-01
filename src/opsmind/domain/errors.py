"""Typed errors for product and inventory operations."""

from uuid import UUID


class DuplicateSkuError(Exception):
    """A product already uses the normalized SKU."""

    def __init__(self, sku: str) -> None:
        self.sku = sku
        super().__init__(sku)


class ProductNotFoundError(Exception):
    """The requested product does not exist."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(str(product_id))


class InventoryNotFoundError(Exception):
    """The product exists but has no inventory position."""

    def __init__(self, product_id: UUID) -> None:
        self.product_id = product_id
        super().__init__(str(product_id))
