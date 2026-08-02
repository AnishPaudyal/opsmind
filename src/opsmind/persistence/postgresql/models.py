"""Persistence-internal SQLAlchemy models for operational data."""

from datetime import date
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from opsmind.persistence.postgresql.database import Base

PRODUCT_SKU_UNIQUE_CONSTRAINT = "uq_products_sku"
DEMAND_DATE_UNIQUE_CONSTRAINT = "uq_demand_observations_product_id"


class ProductRow(Base):
    """Database representation of one product."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("sku"),
        CheckConstraint("btrim(sku) <> ''", name="sku_nonblank"),
        CheckConstraint("btrim(name) <> ''", name="name_nonblank"),
        CheckConstraint(
            "btrim(unit_of_measure) <> ''",
            name="unit_of_measure_nonblank",
        ),
        CheckConstraint("lead_time_days >= 0", name="lead_time_days_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    sku: Mapped[str] = mapped_column(String, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    unit_of_measure: Mapped[str] = mapped_column(String, nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False)


class InventoryPositionRow(Base):
    """Database representation of one product's current inventory."""

    __tablename__ = "inventory_positions"
    __table_args__ = (
        CheckConstraint(
            "on_hand_quantity >= 0",
            name="on_hand_quantity_nonnegative",
        ),
        CheckConstraint(
            "allocated_quantity >= 0",
            name="allocated_quantity_nonnegative",
        ),
    )

    product_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    on_hand_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_quantity: Mapped[int] = mapped_column(Integer, nullable=False)


class DemandObservationRow(Base):
    """Database representation of one daily demand observation."""

    __tablename__ = "demand_observations"
    __table_args__ = (
        UniqueConstraint("product_id", "demand_date"),
        CheckConstraint("quantity >= 0", name="quantity_nonnegative"),
        Index(None, "product_id"),
    )

    id: Mapped[UUID] = mapped_column(PostgreSQLUUID(as_uuid=True), primary_key=True)
    product_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    demand_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
