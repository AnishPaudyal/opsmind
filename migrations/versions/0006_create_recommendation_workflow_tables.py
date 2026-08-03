"""Create recommendation workflow persistence tables.

Revision ID: 0006_workflow_persistence
Revises: 0005_operational_data
Create Date: 2026-08-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_workflow_persistence"
down_revision: str | None = "0005_operational_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create durable recommendation workflow and audit tables."""
    op.create_table(
        "recommendation_reviews",
        sa.Column(
            "recommendation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("unit_of_measure", sa.String(), nullable=False),
        sa.Column("recommendation_policy", sa.String(), nullable=False),
        sa.Column("recommendation_status", sa.String(), nullable=False),
        sa.Column("forecast_method", sa.String(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column(
            "lookback_observations_requested",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("observations_used", sa.Integer(), nullable=False),
        sa.Column("training_start_date", sa.Date(), nullable=False),
        sa.Column("training_end_date", sa.Date(), nullable=False),
        sa.Column("average_daily_demand", sa.Numeric(), nullable=False),
        sa.Column("lead_time_days", sa.Integer(), nullable=False),
        sa.Column("on_hand_quantity", sa.Integer(), nullable=False),
        sa.Column("allocated_quantity", sa.Integer(), nullable=False),
        sa.Column("available_inventory", sa.Integer(), nullable=False),
        sa.Column(
            "forecasted_lead_time_demand",
            sa.Numeric(),
            nullable=False,
        ),
        sa.Column(
            "projected_inventory_balance",
            sa.Numeric(),
            nullable=False,
        ),
        sa.Column(
            "projected_shortage_quantity",
            sa.Numeric(),
            nullable=False,
        ),
        sa.Column(
            "recommended_reorder_quantity",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            "allocated_quantity >= 0",
            name=op.f("ck_recommendation_reviews_allocated_quantity_nonnegative"),
        ),
        sa.CheckConstraint(
            "available_inventory = on_hand_quantity - allocated_quantity",
            name=op.f("ck_recommendation_reviews_available_inventory_consistent"),
        ),
        sa.CheckConstraint(
            "average_daily_demand >= 0",
            name=op.f("ck_recommendation_reviews_average_daily_demand_nonnegative"),
        ),
        sa.CheckConstraint(
            "forecast_method = 'simple_mean'",
            name=op.f("ck_recommendation_reviews_forecast_method_supported"),
        ),
        sa.CheckConstraint(
            "forecasted_lead_time_demand >= 0",
            name=op.f(
                "ck_recommendation_reviews_forecast_lead_time_demand_nonnegative"
            ),
        ),
        sa.CheckConstraint(
            "lead_time_days >= 0",
            name=op.f("ck_recommendation_reviews_lead_time_days_nonnegative"),
        ),
        sa.CheckConstraint(
            "lookback_observations_requested > 0",
            name=op.f("ck_recommendation_reviews_lookback_observations_positive"),
        ),
        sa.CheckConstraint(
            "observations_used > 0",
            name=op.f("ck_recommendation_reviews_observations_used_positive"),
        ),
        sa.CheckConstraint(
            "observations_used <= lookback_observations_requested",
            name=op.f("ck_recommendation_reviews_observations_within_lookback"),
        ),
        sa.CheckConstraint(
            "on_hand_quantity >= 0",
            name=op.f("ck_recommendation_reviews_on_hand_quantity_nonnegative"),
        ),
        sa.CheckConstraint(
            "projected_shortage_quantity > 0",
            name=op.f("ck_recommendation_reviews_projected_shortage_quantity_positive"),
        ),
        sa.CheckConstraint(
            "recommendation_policy = 'projected_shortage_ceiling'",
            name=op.f("ck_recommendation_reviews_recommendation_policy_supported"),
        ),
        sa.CheckConstraint(
            "recommendation_status = 'reorder_recommended'",
            name=op.f("ck_recommendation_reviews_recommendation_status_actionable"),
        ),
        sa.CheckConstraint(
            "recommended_reorder_quantity > 0",
            name=op.f("ck_recommendation_reviews_recommended_quantity_positive"),
        ),
        sa.CheckConstraint(
            "("
            "review_status = 'pending_review' "
            "AND decision_id IS NULL"
            ") OR ("
            "review_status IN ('approved', 'rejected') "
            "AND decision_id IS NOT NULL"
            ")",
            name=op.f("ck_recommendation_reviews_review_decision_shape"),
        ),
        sa.CheckConstraint(
            "review_status IN ('pending_review', 'approved', 'rejected')",
            name=op.f("ck_recommendation_reviews_review_status_supported"),
        ),
        sa.CheckConstraint(
            "training_end_date >= training_start_date",
            name=op.f("ck_recommendation_reviews_training_date_order"),
        ),
        sa.CheckConstraint(
            "btrim(unit_of_measure) <> ''",
            name=op.f("ck_recommendation_reviews_unit_of_measure_nonblank"),
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name=op.f("fk_recommendation_reviews_product_id_products"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "recommendation_id",
            name=op.f("pk_recommendation_reviews"),
        ),
    )

    op.create_table(
        "recommendation_decisions",
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "recommendation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("decision_type", sa.String(), nullable=False),
        sa.Column("decided_by", sa.String(), nullable=False),
        sa.Column(
            "decided_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "approved_quantity",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("note", sa.String(), nullable=True),
        sa.CheckConstraint(
            "btrim(decided_by) <> ''",
            name=op.f("ck_recommendation_decisions_decided_by_nonblank"),
        ),
        sa.CheckConstraint(
            "("
            "decision_type = 'approved' "
            "AND approved_quantity IS NOT NULL "
            "AND approved_quantity > 0"
            ") OR ("
            "decision_type = 'rejected' "
            "AND approved_quantity IS NULL "
            "AND note IS NOT NULL "
            "AND btrim(note) <> ''"
            ")",
            name=op.f("ck_recommendation_decisions_decision_shape"),
        ),
        sa.CheckConstraint(
            "decision_type IN ('approved', 'rejected')",
            name=op.f("ck_recommendation_decisions_decision_type_supported"),
        ),
        sa.CheckConstraint(
            "note IS NULL OR btrim(note) <> ''",
            name=op.f("ck_recommendation_decisions_note_optional_nonblank"),
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendation_reviews.recommendation_id"],
            name=op.f("fk_recommendation_decisions_review"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "decision_id",
            name=op.f("pk_recommendation_decisions"),
        ),
        sa.UniqueConstraint(
            "recommendation_id",
            name=op.f("uq_recommendation_decisions_recommendation_id"),
        ),
        sa.UniqueConstraint(
            "recommendation_id",
            "decision_id",
            name=op.f("uq_recommendation_decisions_recommendation_id_decision_id"),
        ),
    )

    op.create_foreign_key(
        op.f("fk_recommendation_reviews_decision_pair"),
        "recommendation_reviews",
        "recommendation_decisions",
        ["recommendation_id", "decision_id"],
        ["recommendation_id", "decision_id"],
        ondelete="RESTRICT",
    )

    op.create_table(
        "recommendation_audit_events",
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "recommendation_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("review_status", sa.String(), nullable=False),
        sa.Column(
            "decision_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("actor", sa.String(), nullable=True),
        sa.Column(
            "recommended_reorder_quantity",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "approved_quantity",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("note", sa.String(), nullable=True),
        sa.CheckConstraint(
            "actor IS NULL OR btrim(actor) <> ''",
            name=op.f("ck_recommendation_audit_events_actor_optional_nonblank"),
        ),
        sa.CheckConstraint(
            "("
            "event_type = 'review_created' "
            "AND sequence_number = 1 "
            "AND review_status = 'pending_review' "
            "AND decision_id IS NULL "
            "AND actor IS NULL "
            "AND approved_quantity IS NULL "
            "AND note IS NULL"
            ") OR ("
            "event_type = 'recommendation_approved' "
            "AND sequence_number = 2 "
            "AND review_status = 'approved' "
            "AND decision_id IS NOT NULL "
            "AND actor IS NOT NULL "
            "AND btrim(actor) <> '' "
            "AND approved_quantity IS NOT NULL "
            "AND approved_quantity > 0"
            ") OR ("
            "event_type = 'recommendation_rejected' "
            "AND sequence_number = 2 "
            "AND review_status = 'rejected' "
            "AND decision_id IS NOT NULL "
            "AND actor IS NOT NULL "
            "AND btrim(actor) <> '' "
            "AND approved_quantity IS NULL "
            "AND note IS NOT NULL "
            "AND btrim(note) <> ''"
            ")",
            name=op.f("ck_recommendation_audit_events_event_shape"),
        ),
        sa.CheckConstraint(
            "event_type IN ("
            "'review_created', "
            "'recommendation_approved', "
            "'recommendation_rejected'"
            ")",
            name=op.f("ck_recommendation_audit_events_event_type_supported"),
        ),
        sa.CheckConstraint(
            "note IS NULL OR btrim(note) <> ''",
            name=op.f("ck_recommendation_audit_events_note_optional_nonblank"),
        ),
        sa.CheckConstraint(
            "recommended_reorder_quantity > 0",
            name=op.f("ck_recommendation_audit_events_recommended_quantity_positive"),
        ),
        sa.CheckConstraint(
            "review_status IN ('pending_review', 'approved', 'rejected')",
            name=op.f("ck_recommendation_audit_events_review_status_supported"),
        ),
        sa.CheckConstraint(
            "sequence_number > 0",
            name=op.f("ck_recommendation_audit_events_sequence_number_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id", "decision_id"],
            [
                "recommendation_decisions.recommendation_id",
                "recommendation_decisions.decision_id",
            ],
            name=op.f("fk_recommendation_audit_events_decision_pair"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["recommendation_reviews.recommendation_id"],
            name=op.f("fk_recommendation_audit_events_review"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "event_id",
            name=op.f("pk_recommendation_audit_events"),
        ),
        sa.UniqueConstraint(
            "decision_id",
            name=op.f("uq_recommendation_audit_events_decision_id"),
        ),
        sa.UniqueConstraint(
            "recommendation_id",
            "sequence_number",
            name=op.f("uq_recommendation_audit_events_recommendation_id"),
        ),
    )

    op.create_index(
        op.f("ix_recommendation_reviews_product_id"),
        "recommendation_reviews",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    """Drop workflow resources in dependency-safe order."""
    op.drop_table("recommendation_audit_events")

    op.drop_constraint(
        op.f("fk_recommendation_reviews_decision_pair"),
        "recommendation_reviews",
        type_="foreignkey",
    )

    op.drop_table("recommendation_decisions")

    op.drop_index(
        op.f("ix_recommendation_reviews_product_id"),
        table_name="recommendation_reviews",
    )
    op.drop_table("recommendation_reviews")
