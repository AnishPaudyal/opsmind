"""Product, inventory, and demand repository interface."""

from datetime import date
from typing import Protocol
from uuid import UUID

from opsmind.domain.demand import DemandObservation
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product


class ProductInventoryRepository(Protocol):
    """Product and inventory operations required by the business API."""

    def create_product(self, product: Product) -> Product:
        """Store and return a product with a unique normalized SKU."""
        ...

    def list_products(self) -> tuple[Product, ...]:
        """Return products in deterministic normalized-SKU order."""
        ...

    def get_product(self, product_id: UUID) -> Product:
        """Return one product or raise a typed not-found error."""
        ...

    def set_inventory(self, inventory: InventoryPosition) -> InventoryPosition:
        """Set or replace inventory for an existing product."""
        ...

    def get_inventory(self, product_id: UUID) -> InventoryPosition:
        """Return inventory while distinguishing missing product and position."""
        ...

    def add_demand_observations(
        self,
        product_id: UUID,
        observations: tuple[DemandObservation, ...],
    ) -> tuple[DemandObservation, ...]:
        """Atomically store one chronological demand batch for a product."""
        ...

    def list_demand_observations(
        self,
        product_id: UUID,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[DemandObservation, ...]:
        """Return chronological demand within optional inclusive bounds."""
        ...
