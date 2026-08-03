"""Persistence-internal SQLAlchemy models for operational and workflow data."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from opsmind.persistence.postgresql.database import Base

PRODUCT_SKU_UNIQUE_CONSTRAINT = "uq_products_sku"
DEMAND_DATE_UNIQUE_CONSTRAINT = "uq_demand_observations_product_id"

RECOMMENDATION_DECISION_REVIEW_UNIQUE_CONSTRAINT = (
    "uq_recommendation_decisions_recommendation_id"
)
RECOMMENDATION_DECISION_PAIR_UNIQUE_CONSTRAINT = (
    "uq_recommendation_decisions_recommendation_id_decision_id"
)
RECOMMENDATION_REVIEW_DECISION_FOREIGN_KEY = "fk_recommendation_reviews_decision_pair"
RECOMMENDATION_DECISION_REVIEW_FOREIGN_KEY = "fk_recommendation_decisions_review"
RECOMMENDATION_AUDIT_DECISION_FOREIGN_KEY = (
    "fk_recommendation_audit_events_decision_pair"
)
RECOMMENDATION_AUDIT_REVIEW_FOREIGN_KEY = "fk_recommendation_audit_events_review"

RECOMMENDATION_AUDIT_SEQUENCE_UNIQUE_CONSTRAINT = (
    "uq_recommendation_audit_events_recommendation_id"
)
RECOMMENDATION_AUDIT_DECISION_UNIQUE_CONSTRAINT = (
    "uq_recommendation_audit_events_decision_id"
)


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


class RecommendationReviewRow(Base):
    """Database representation of one immutable recommendation snapshot."""

    __tablename__ = "recommendation_reviews"
    __table_args__ = (
        CheckConstraint(
            "btrim(unit_of_measure) <> ''",
            name="unit_of_measure_nonblank",
        ),
        CheckConstraint(
            "recommendation_policy = 'projected_shortage_ceiling'",
            name="recommendation_policy_supported",
        ),
        CheckConstraint(
            "recommendation_status = 'reorder_recommended'",
            name="recommendation_status_actionable",
        ),
        CheckConstraint(
            "forecast_method = 'simple_mean'",
            name="forecast_method_supported",
        ),
        CheckConstraint(
            "lookback_observations_requested > 0",
            name="lookback_observations_positive",
        ),
        CheckConstraint(
            "observations_used > 0",
            name="observations_used_positive",
        ),
        CheckConstraint(
            "observations_used <= lookback_observations_requested",
            name="observations_within_lookback",
        ),
        CheckConstraint(
            "training_end_date >= training_start_date",
            name="training_date_order",
        ),
        CheckConstraint(
            "average_daily_demand >= 0",
            name="average_daily_demand_nonnegative",
        ),
        CheckConstraint(
            "lead_time_days >= 0",
            name="lead_time_days_nonnegative",
        ),
        CheckConstraint(
            "on_hand_quantity >= 0",
            name="on_hand_quantity_nonnegative",
        ),
        CheckConstraint(
            "allocated_quantity >= 0",
            name="allocated_quantity_nonnegative",
        ),
        CheckConstraint(
            "available_inventory = on_hand_quantity - allocated_quantity",
            name="available_inventory_consistent",
        ),
        CheckConstraint(
            "forecasted_lead_time_demand >= 0",
            name="forecast_lead_time_demand_nonnegative",
        ),
        CheckConstraint(
            "projected_shortage_quantity > 0",
            name="projected_shortage_quantity_positive",
        ),
        CheckConstraint(
            "recommended_reorder_quantity > 0",
            name="recommended_quantity_positive",
        ),
        CheckConstraint(
            "review_status IN ('pending_review', 'approved', 'rejected')",
            name="review_status_supported",
        ),
        CheckConstraint(
            "("
            "review_status = 'pending_review' AND decision_id IS NULL"
            ") OR ("
            "review_status IN ('approved', 'rejected') "
            "AND decision_id IS NOT NULL"
            ")",
            name="review_decision_shape",
        ),
        ForeignKeyConstraint(
            ["recommendation_id", "decision_id"],
            [
                "recommendation_decisions.recommendation_id",
                "recommendation_decisions.decision_id",
            ],
            name=RECOMMENDATION_REVIEW_DECISION_FOREIGN_KEY,
            ondelete="RESTRICT",
            use_alter=True,
        ),
        Index(None, "product_id"),
    )

    recommendation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    )
    product_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    unit_of_measure: Mapped[str] = mapped_column(String, nullable=False)
    recommendation_policy: Mapped[str] = mapped_column(String, nullable=False)
    recommendation_status: Mapped[str] = mapped_column(String, nullable=False)
    forecast_method: Mapped[str] = mapped_column(String, nullable=False)
    as_of_date: Mapped[date] = mapped_column(Date, nullable=False)
    lookback_observations_requested: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    observations_used: Mapped[int] = mapped_column(Integer, nullable=False)
    training_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    training_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    average_daily_demand: Mapped[Decimal] = mapped_column(
        Numeric(),
        nullable=False,
    )
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    on_hand_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    allocated_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    available_inventory: Mapped[int] = mapped_column(Integer, nullable=False)
    forecasted_lead_time_demand: Mapped[Decimal] = mapped_column(
        Numeric(),
        nullable=False,
    )
    projected_inventory_balance: Mapped[Decimal] = mapped_column(
        Numeric(),
        nullable=False,
    )
    projected_shortage_quantity: Mapped[Decimal] = mapped_column(
        Numeric(),
        nullable=False,
    )
    recommended_reorder_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    decision_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )


class RecommendationDecisionRow(Base):
    """Database representation of one immutable terminal decision."""

    __tablename__ = "recommendation_decisions"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_id",
            name=RECOMMENDATION_DECISION_REVIEW_UNIQUE_CONSTRAINT,
        ),
        UniqueConstraint(
            "recommendation_id",
            "decision_id",
            name=RECOMMENDATION_DECISION_PAIR_UNIQUE_CONSTRAINT,
        ),
        CheckConstraint(
            "decision_type IN ('approved', 'rejected')",
            name="decision_type_supported",
        ),
        CheckConstraint(
            "btrim(decided_by) <> ''",
            name="decided_by_nonblank",
        ),
        CheckConstraint(
            "note IS NULL OR btrim(note) <> ''",
            name="note_optional_nonblank",
        ),
        CheckConstraint(
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
            name="decision_shape",
        ),
    )

    decision_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    )
    recommendation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "recommendation_reviews.recommendation_id",
            name=RECOMMENDATION_DECISION_REVIEW_FOREIGN_KEY,
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    decision_type: Mapped[str] = mapped_column(String, nullable=False)
    decided_by: Mapped[str] = mapped_column(String, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    approved_quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(String, nullable=True)


class RecommendationAuditEventRow(Base):
    """Database representation of one append-only workflow event."""

    __tablename__ = "recommendation_audit_events"
    __table_args__ = (
        UniqueConstraint(
            "recommendation_id",
            "sequence_number",
            name=RECOMMENDATION_AUDIT_SEQUENCE_UNIQUE_CONSTRAINT,
        ),
        UniqueConstraint(
            "decision_id",
            name=RECOMMENDATION_AUDIT_DECISION_UNIQUE_CONSTRAINT,
        ),
        CheckConstraint(
            "sequence_number > 0",
            name="sequence_number_positive",
        ),
        CheckConstraint(
            "event_type IN ("
            "'review_created', "
            "'recommendation_approved', "
            "'recommendation_rejected'"
            ")",
            name="event_type_supported",
        ),
        CheckConstraint(
            "review_status IN ('pending_review', 'approved', 'rejected')",
            name="review_status_supported",
        ),
        CheckConstraint(
            "actor IS NULL OR btrim(actor) <> ''",
            name="actor_optional_nonblank",
        ),
        CheckConstraint(
            "note IS NULL OR btrim(note) <> ''",
            name="note_optional_nonblank",
        ),
        CheckConstraint(
            "recommended_reorder_quantity > 0",
            name="recommended_quantity_positive",
        ),
        CheckConstraint(
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
            name="event_shape",
        ),
        ForeignKeyConstraint(
            ["recommendation_id", "decision_id"],
            [
                "recommendation_decisions.recommendation_id",
                "recommendation_decisions.decision_id",
            ],
            name=RECOMMENDATION_AUDIT_DECISION_FOREIGN_KEY,
            ondelete="RESTRICT",
        ),
    )

    event_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
    )
    recommendation_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey(
            "recommendation_reviews.recommendation_id",
            name=RECOMMENDATION_AUDIT_REVIEW_FOREIGN_KEY,
            ondelete="RESTRICT",
        ),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    review_status: Mapped[str] = mapped_column(String, nullable=False)
    decision_id: Mapped[UUID | None] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=True,
    )
    actor: Mapped[str | None] = mapped_column(String, nullable=True)
    recommended_reorder_quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    approved_quantity: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(String, nullable=True)
