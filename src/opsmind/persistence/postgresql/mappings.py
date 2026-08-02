"""Explicit mappings between PostgreSQL rows and immutable domain objects."""

from opsmind.domain.demand import DemandObservation
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
from opsmind.persistence.postgresql.models import (
    DemandObservationRow,
    InventoryPositionRow,
    ProductRow,
)


def product_row_to_domain(row: ProductRow) -> Product:
    """Return a domain product detached from its ORM row."""
    return Product(
        id=row.id,
        sku=row.sku,
        name=row.name,
        unit_of_measure=row.unit_of_measure,
        lead_time_days=row.lead_time_days,
        is_active=row.is_active,
    )


def inventory_row_to_domain(row: InventoryPositionRow) -> InventoryPosition:
    """Return a domain inventory position detached from its ORM row."""
    return InventoryPosition(
        product_id=row.product_id,
        on_hand_quantity=row.on_hand_quantity,
        allocated_quantity=row.allocated_quantity,
    )


def demand_row_to_domain(row: DemandObservationRow) -> DemandObservation:
    """Return a domain demand observation detached from its ORM row."""
    return DemandObservation(
        product_id=row.product_id,
        demand_date=row.demand_date,
        quantity=row.quantity,
        id=row.id,
    )
