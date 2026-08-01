"""Isolated in-memory product and inventory repository."""

from datetime import date
from threading import RLock
from uuid import UUID

from opsmind.domain.demand import (
    DemandObservation,
    validate_demand_batch,
    validate_demand_date_range,
)
from opsmind.domain.errors import (
    DuplicateDemandDateError,
    DuplicateSkuError,
    InventoryNotFoundError,
    ProductNotFoundError,
)
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product, normalize_sku


class InMemoryProductInventoryRepository:
    """Store product and inventory state for one application instance."""

    def __init__(self) -> None:
        self._products: dict[UUID, Product] = {}
        self._product_ids_by_sku: dict[str, UUID] = {}
        self._inventory: dict[UUID, InventoryPosition] = {}
        self._demand: dict[UUID, dict[date, DemandObservation]] = {}
        self._lock = RLock()

    def create_product(self, product: Product) -> Product:
        """Store a product after enforcing canonical SKU uniqueness."""
        normalized_sku = normalize_sku(product.sku)
        with self._lock:
            if normalized_sku in self._product_ids_by_sku:
                raise DuplicateSkuError(normalized_sku)
            self._products[product.id] = product
            self._product_ids_by_sku[normalized_sku] = product.id
        return product

    def list_products(self) -> tuple[Product, ...]:
        """Return an immutable, deterministic view of stored products."""
        with self._lock:
            return tuple(sorted(self._products.values(), key=lambda item: item.sku))

    def get_product(self, product_id: UUID) -> Product:
        """Return a product by UUID."""
        with self._lock:
            try:
                return self._products[product_id]
            except KeyError:
                raise ProductNotFoundError(product_id) from None

    def set_inventory(self, inventory: InventoryPosition) -> InventoryPosition:
        """Set or replace inventory for an existing product."""
        with self._lock:
            if inventory.product_id not in self._products:
                raise ProductNotFoundError(inventory.product_id)
            self._inventory[inventory.product_id] = inventory
        return inventory

    def get_inventory(self, product_id: UUID) -> InventoryPosition:
        """Return inventory with distinct product and inventory failures."""
        with self._lock:
            if product_id not in self._products:
                raise ProductNotFoundError(product_id)
            try:
                return self._inventory[product_id]
            except KeyError:
                raise InventoryNotFoundError(product_id) from None

    def add_demand_observations(
        self,
        product_id: UUID,
        observations: tuple[DemandObservation, ...],
    ) -> tuple[DemandObservation, ...]:
        """Atomically validate and store a complete demand batch."""
        with self._lock:
            if product_id not in self._products:
                raise ProductNotFoundError(product_id)

            chronological_observations = validate_demand_batch(
                product_id,
                observations,
            )
            existing_observations = self._demand.get(product_id, {})
            for observation in chronological_observations:
                if observation.demand_date in existing_observations:
                    raise DuplicateDemandDateError(
                        product_id,
                        observation.demand_date,
                    )

            stored_observations = self._demand.setdefault(product_id, {})
            stored_observations.update(
                {
                    observation.demand_date: observation
                    for observation in chronological_observations
                }
            )
            return chronological_observations

    def list_demand_observations(
        self,
        product_id: UUID,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[DemandObservation, ...]:
        """Return chronological demand within optional inclusive bounds."""
        with self._lock:
            if product_id not in self._products:
                raise ProductNotFoundError(product_id)
            validate_demand_date_range(start_date, end_date)
            observations = self._demand.get(product_id, {}).values()
            return tuple(
                sorted(
                    (
                        observation
                        for observation in observations
                        if (start_date is None or observation.demand_date >= start_date)
                        and (end_date is None or observation.demand_date <= end_date)
                    ),
                    key=lambda item: item.demand_date,
                )
            )
