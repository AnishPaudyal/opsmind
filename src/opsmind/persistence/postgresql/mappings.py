"""Explicit mappings between PostgreSQL rows and immutable domain objects."""

from uuid import UUID

from opsmind.domain.demand import DemandObservation
from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
from opsmind.domain.recommendation_audit import (
    RecommendationAuditEvent,
    RecommendationAuditEventType,
)
from opsmind.domain.recommendation_review import (
    RecommendationDecision,
    RecommendationDecisionType,
    RecommendationReviewStatus,
    ReorderRecommendationReview,
)
from opsmind.domain.reorder import (
    ReorderRecommendation,
    ReorderRecommendationPolicy,
    ReorderRecommendationStatus,
)
from opsmind.persistence.postgresql.models import (
    DemandObservationRow,
    InventoryPositionRow,
    ProductRow,
    RecommendationAuditEventRow,
    RecommendationDecisionRow,
    RecommendationReviewRow,
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


def _recommendation_row_to_domain(
    row: RecommendationReviewRow,
) -> ReorderRecommendation:
    """Reconstruct the immutable recommendation snapshot stored on a review."""
    return ReorderRecommendation(
        product_id=row.product_id,
        unit_of_measure=row.unit_of_measure,
        recommendation_policy=ReorderRecommendationPolicy(row.recommendation_policy),
        recommendation_status=ReorderRecommendationStatus(row.recommendation_status),
        forecast_method=ForecastMethod(row.forecast_method),
        as_of_date=row.as_of_date,
        lookback_observations_requested=(row.lookback_observations_requested),
        observations_used=row.observations_used,
        training_start_date=row.training_start_date,
        training_end_date=row.training_end_date,
        average_daily_demand=row.average_daily_demand,
        lead_time_days=row.lead_time_days,
        on_hand_quantity=row.on_hand_quantity,
        allocated_quantity=row.allocated_quantity,
        available_inventory=row.available_inventory,
        forecasted_lead_time_demand=row.forecasted_lead_time_demand,
        projected_inventory_balance=row.projected_inventory_balance,
        projected_shortage_quantity=row.projected_shortage_quantity,
        recommended_reorder_quantity=row.recommended_reorder_quantity,
    )


def recommendation_decision_row_to_domain(
    row: RecommendationDecisionRow,
) -> RecommendationDecision:
    """Return an immutable terminal decision detached from its ORM row."""
    return RecommendationDecision(
        decision_id=row.decision_id,
        decision_type=RecommendationDecisionType(row.decision_type),
        decided_by=row.decided_by,
        decided_at=row.decided_at,
        approved_quantity=row.approved_quantity,
        note=row.note,
    )


def recommendation_review_rows_to_domain(
    review_row: RecommendationReviewRow,
    decision_row: RecommendationDecisionRow | None,
) -> ReorderRecommendationReview:
    """Reconstruct one review from its snapshot row and optional decision row."""
    if review_row.decision_id is None:
        if decision_row is not None:
            raise ValueError(
                "review without decision_id must not include a decision row"
            )
        decision = None
    else:
        if decision_row is None:
            raise ValueError("review with decision_id requires a decision row")
        if decision_row.recommendation_id != review_row.recommendation_id:
            raise ValueError(
                "decision recommendation_id must match review recommendation_id"
            )
        if decision_row.decision_id != review_row.decision_id:
            raise ValueError("decision_id must match the review decision pointer")
        decision = recommendation_decision_row_to_domain(decision_row)

    return ReorderRecommendationReview(
        recommendation_id=review_row.recommendation_id,
        recommendation=_recommendation_row_to_domain(review_row),
        review_status=RecommendationReviewStatus(review_row.review_status),
        created_at=review_row.created_at,
        decision=decision,
    )


def recommendation_audit_event_row_to_domain(
    row: RecommendationAuditEventRow,
) -> RecommendationAuditEvent:
    """Return an immutable audit event detached from its ORM row."""
    return RecommendationAuditEvent(
        event_id=row.event_id,
        recommendation_id=row.recommendation_id,
        sequence_number=row.sequence_number,
        event_type=RecommendationAuditEventType(row.event_type),
        occurred_at=row.occurred_at,
        review_status=RecommendationReviewStatus(row.review_status),
        decision_id=row.decision_id,
        actor=row.actor,
        recommended_reorder_quantity=row.recommended_reorder_quantity,
        approved_quantity=row.approved_quantity,
        note=row.note,
    )


def recommendation_review_to_row(
    review: ReorderRecommendationReview,
) -> RecommendationReviewRow:
    """Flatten one immutable review and recommendation snapshot into a row."""
    recommendation = review.recommendation
    decision_id = None if review.decision is None else review.decision.decision_id

    return RecommendationReviewRow(
        recommendation_id=review.recommendation_id,
        product_id=recommendation.product_id,
        unit_of_measure=recommendation.unit_of_measure,
        recommendation_policy=recommendation.recommendation_policy.value,
        recommendation_status=recommendation.recommendation_status.value,
        forecast_method=recommendation.forecast_method.value,
        as_of_date=recommendation.as_of_date,
        lookback_observations_requested=(
            recommendation.lookback_observations_requested
        ),
        observations_used=recommendation.observations_used,
        training_start_date=recommendation.training_start_date,
        training_end_date=recommendation.training_end_date,
        average_daily_demand=recommendation.average_daily_demand,
        lead_time_days=recommendation.lead_time_days,
        on_hand_quantity=recommendation.on_hand_quantity,
        allocated_quantity=recommendation.allocated_quantity,
        available_inventory=recommendation.available_inventory,
        forecasted_lead_time_demand=(recommendation.forecasted_lead_time_demand),
        projected_inventory_balance=(recommendation.projected_inventory_balance),
        projected_shortage_quantity=(recommendation.projected_shortage_quantity),
        recommended_reorder_quantity=(recommendation.recommended_reorder_quantity),
        review_status=review.review_status.value,
        created_at=review.created_at,
        decision_id=decision_id,
    )


def recommendation_decision_to_row(
    recommendation_id: UUID,
    decision: RecommendationDecision,
) -> RecommendationDecisionRow:
    """Convert one immutable terminal decision into a persistence row."""
    return RecommendationDecisionRow(
        decision_id=decision.decision_id,
        recommendation_id=recommendation_id,
        decision_type=decision.decision_type.value,
        decided_by=decision.decided_by,
        decided_at=decision.decided_at,
        approved_quantity=decision.approved_quantity,
        note=decision.note,
    )


def recommendation_audit_event_to_row(
    event: RecommendationAuditEvent,
) -> RecommendationAuditEventRow:
    """Convert one immutable workflow audit event into a persistence row."""
    return RecommendationAuditEventRow(
        event_id=event.event_id,
        recommendation_id=event.recommendation_id,
        sequence_number=event.sequence_number,
        event_type=event.event_type.value,
        occurred_at=event.occurred_at,
        review_status=event.review_status.value,
        decision_id=event.decision_id,
        actor=event.actor,
        recommended_reorder_quantity=(event.recommended_reorder_quantity),
        approved_quantity=event.approved_quantity,
        note=event.note,
    )
