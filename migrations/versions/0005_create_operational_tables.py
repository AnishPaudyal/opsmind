"""Create operational product, inventory, and demand tables.

Revision ID: 0005_operational_data
Revises: None
Create Date: 2026-08-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_operational_data"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the durable operational-data schema."""
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("unit_of_measure", sa.String(), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "lead_time_days >= 0",
            name=op.f("ck_products_lead_time_days_nonnegative"),
        ),
        sa.CheckConstraint(
            "btrim(name) <> ''",
            name=op.f("ck_products_name_nonblank"),
        ),
        sa.CheckConstraint(
            "btrim(sku) <> ''",
            name=op.f("ck_products_sku_nonblank"),
        ),
        sa.CheckConstraint(
            "btrim(unit_of_measure) <> ''",
            name=op.f("ck_products_unit_of_measure_nonblank"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_products")),
        sa.UniqueConstraint("sku", name=op.f("uq_products_sku")),
    )
    op.create_table(
        "inventory_positions",
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("on_hand_quantity", sa.Integer(), nullable=False),
        sa.Column("allocated_quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "allocated_quantity >= 0",
            name=op.f("ck_inventory_positions_allocated_quantity_nonnegative"),
        ),
        sa.CheckConstraint(
            "on_hand_quantity >= 0",
            name=op.f("ck_inventory_positions_on_hand_quantity_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_inventory_positions_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "product_id",
            name=op.f("pk_inventory_positions"),
        ),
    )
    op.create_table(
        "demand_observations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("demand_date", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "quantity >= 0",
            name=op.f("ck_demand_observations_quantity_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_demand_observations_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_demand_observations")),
        sa.UniqueConstraint(
            "product_id",
            "demand_date",
            name=op.f("uq_demand_observations_product_id"),
        ),
    )
    op.create_index(
        op.f("ix_demand_observations_product_id"),
        "demand_observations",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop operational resources in dependency-safe order."""
    op.drop_index(
        op.f("ix_demand_observations_product_id"),
        table_name="demand_observations",
    )
    op.drop_table("demand_observations")
    op.drop_table("inventory_positions")
    op.drop_table("products")
