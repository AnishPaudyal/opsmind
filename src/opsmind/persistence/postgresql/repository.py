"""Synchronous PostgreSQL implementation of operational repository behavior."""

from collections.abc import Iterable
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from opsmind.persistence.postgresql.database import SessionFactory
from opsmind.persistence.postgresql.mappings import (
    demand_row_to_domain,
    inventory_row_to_domain,
    product_row_to_domain,
)
from opsmind.persistence.postgresql.models import (
    DEMAND_DATE_UNIQUE_CONSTRAINT,
    PRODUCT_SKU_UNIQUE_CONSTRAINT,
    DemandObservationRow,
    InventoryPositionRow,
    ProductRow,
)


def _constraint_name(error: IntegrityError) -> str | None:
    diagnostic = getattr(error.orig, "diag", None)
    name = getattr(diagnostic, "constraint_name", None)
    return name if isinstance(name, str) else None


class PostgresProductInventoryRepository:
    """Persist products, inventory, and demand through short-lived sessions."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create_product(self, product: Product) -> Product:
        """Persist a product and translate only canonical-SKU uniqueness."""
        normalized_sku = normalize_sku(product.sku)
        with self._session_factory() as session:
            row = ProductRow(
                id=product.id,
                sku=normalized_sku,
                name=product.name,
                unit_of_measure=product.unit_of_measure,
                lead_time_days=product.lead_time_days,
                is_active=product.is_active,
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                if _constraint_name(error) == PRODUCT_SKU_UNIQUE_CONSTRAINT:
                    raise DuplicateSkuError(normalized_sku) from None
                raise
            return product_row_to_domain(row)

    def list_products(self) -> tuple[Product, ...]:
        """Return products in canonical SKU order."""
        with self._session_factory() as session:
            rows = session.scalars(select(ProductRow).order_by(ProductRow.sku)).all()
            return tuple(product_row_to_domain(row) for row in rows)

    def get_product(self, product_id: UUID) -> Product:
        """Return one product or the existing domain not-found error."""
        with self._session_factory() as session:
            row = session.get(ProductRow, product_id)
            if row is None:
                raise ProductNotFoundError(product_id)
            return product_row_to_domain(row)

    def set_inventory(self, inventory: InventoryPosition) -> InventoryPosition:
        """Atomically replace one complete inventory position using an upsert."""
        with self._session_factory() as session:
            self._ensure_product_exists(session, inventory.product_id)
            statement = (
                insert(InventoryPositionRow)
                .values(
                    product_id=inventory.product_id,
                    on_hand_quantity=inventory.on_hand_quantity,
                    allocated_quantity=inventory.allocated_quantity,
                )
                .on_conflict_do_update(
                    index_elements=[InventoryPositionRow.product_id],
                    set_={
                        "on_hand_quantity": inventory.on_hand_quantity,
                        "allocated_quantity": inventory.allocated_quantity,
                    },
                )
            )
            try:
                session.execute(statement)
                session.commit()
            except IntegrityError:
                session.rollback()
                raise
            return inventory

    def get_inventory(self, product_id: UUID) -> InventoryPosition:
        """Return inventory while preserving distinct missing-state errors."""
        with self._session_factory() as session:
            self._ensure_product_exists(session, product_id)
            row = session.get(InventoryPositionRow, product_id)
            if row is None:
                raise InventoryNotFoundError(product_id)
            return inventory_row_to_domain(row)

    def add_demand_observations(
        self,
        product_id: UUID,
        observations: tuple[DemandObservation, ...],
    ) -> tuple[DemandObservation, ...]:
        """Persist one validated demand batch in a single transaction."""
        chronological = validate_demand_batch(product_id, observations)
        with self._session_factory() as session:
            self._ensure_product_exists(session, product_id)
            rows = [
                DemandObservationRow(
                    id=observation.id,
                    product_id=observation.product_id,
                    demand_date=observation.demand_date,
                    quantity=observation.quantity,
                )
                for observation in chronological
            ]
            session.add_all(rows)
            try:
                session.commit()
            except IntegrityError as error:
                session.rollback()
                if _constraint_name(error) == DEMAND_DATE_UNIQUE_CONSTRAINT:
                    conflict = self._find_conflicting_demand_date(
                        session,
                        product_id,
                        (observation.demand_date for observation in chronological),
                    )
                    if conflict is not None:
                        raise DuplicateDemandDateError(product_id, conflict) from None
                raise
            return tuple(demand_row_to_domain(row) for row in rows)

    def list_demand_observations(
        self,
        product_id: UUID,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[DemandObservation, ...]:
        """Return chronological demand within optional inclusive bounds."""
        validate_demand_date_range(start_date, end_date)
        with self._session_factory() as session:
            self._ensure_product_exists(session, product_id)
            statement = select(DemandObservationRow).where(
                DemandObservationRow.product_id == product_id
            )
            if start_date is not None:
                statement = statement.where(
                    DemandObservationRow.demand_date >= start_date
                )
            if end_date is not None:
                statement = statement.where(
                    DemandObservationRow.demand_date <= end_date
                )
            rows = session.scalars(
                statement.order_by(DemandObservationRow.demand_date)
            ).all()
            return tuple(demand_row_to_domain(row) for row in rows)

    @staticmethod
    def _ensure_product_exists(session: Session, product_id: UUID) -> None:
        exists = session.scalar(
            select(ProductRow.id).where(ProductRow.id == product_id)
        )
        if exists is None:
            raise ProductNotFoundError(product_id)

    @staticmethod
    def _find_conflicting_demand_date(
        session: Session,
        product_id: UUID,
        demand_dates: Iterable[date],
    ) -> date | None:
        return session.scalar(
            select(DemandObservationRow.demand_date)
            .where(
                DemandObservationRow.product_id == product_id,
                DemandObservationRow.demand_date.in_(tuple(demand_dates)),
            )
            .order_by(DemandObservationRow.demand_date)
            .limit(1)
        )
