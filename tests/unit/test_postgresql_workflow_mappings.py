"""Tests for explicit PostgreSQL recommendation-workflow mappings."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.recommendation_audit import (
    create_review_created_audit_event,
    create_review_decision_audit_event,
)
from opsmind.domain.recommendation_review import (
    ReorderRecommendationReview,
    approve_recommendation,
    create_recommendation_review,
    reject_recommendation,
)
from opsmind.domain.reorder import (
    ReorderRecommendation,
    ReorderRecommendationPolicy,
    ReorderRecommendationStatus,
)
from opsmind.persistence.postgresql.mappings import (
    recommendation_audit_event_row_to_domain,
    recommendation_audit_event_to_row,
    recommendation_decision_to_row,
    recommendation_review_rows_to_domain,
    recommendation_review_to_row,
)

PRODUCT_ID = UUID("10000000-0000-0000-0000-000000000001")
RECOMMENDATION_ID = UUID("20000000-0000-0000-0000-000000000001")
OTHER_RECOMMENDATION_ID = UUID("20000000-0000-0000-0000-000000000002")
APPROVAL_ID = UUID("30000000-0000-0000-0000-000000000001")
REJECTION_ID = UUID("30000000-0000-0000-0000-000000000002")
OTHER_DECISION_ID = UUID("30000000-0000-0000-0000-000000000003")
CREATION_EVENT_ID = UUID("40000000-0000-0000-0000-000000000001")
APPROVAL_EVENT_ID = UUID("40000000-0000-0000-0000-000000000002")
REJECTION_EVENT_ID = UUID("40000000-0000-0000-0000-000000000003")

CREATED_AT = datetime(2026, 8, 3, 15, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)


def make_recommendation() -> ReorderRecommendation:
    """Build one actionable immutable recommendation snapshot."""
    return ReorderRecommendation(
        product_id=PRODUCT_ID,
        unit_of_measure="units",
        recommendation_policy=(ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING),
        recommendation_status=(ReorderRecommendationStatus.REORDER_RECOMMENDED),
        forecast_method=ForecastMethod.SIMPLE_MEAN,
        as_of_date=date(2026, 8, 3),
        lookback_observations_requested=30,
        observations_used=30,
        training_start_date=date(2026, 7, 5),
        training_end_date=date(2026, 8, 3),
        average_daily_demand=Decimal("4.25"),
        lead_time_days=7,
        on_hand_quantity=20,
        allocated_quantity=25,
        available_inventory=-5,
        forecasted_lead_time_demand=Decimal("29.75"),
        projected_inventory_balance=Decimal("-34.75"),
        projected_shortage_quantity=Decimal("34.75"),
        recommended_reorder_quantity=35,
    )


def make_pending_review() -> ReorderRecommendationReview:
    """Build one valid pending recommendation review."""
    return create_recommendation_review(
        recommendation_id=RECOMMENDATION_ID,
        recommendation=make_recommendation(),
        created_at=CREATED_AT,
    )


def make_approved_review() -> ReorderRecommendationReview:
    """Build one valid approved recommendation review."""
    return approve_recommendation(
        review=make_pending_review(),
        decision_id=APPROVAL_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        approved_quantity=36,
        note="Expedite replenishment",
    )


def make_rejected_review() -> ReorderRecommendationReview:
    """Build one valid rejected recommendation review."""
    return reject_recommendation(
        review=make_pending_review(),
        decision_id=REJECTION_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        reason="Supplier delivery is already confirmed",
    )


def test_pending_review_round_trip_preserves_complete_snapshot() -> None:
    """A pending review survives row conversion without losing typed values."""
    review = make_pending_review()

    row = recommendation_review_to_row(review)
    restored = recommendation_review_rows_to_domain(row, None)

    assert restored == review
    assert row.decision_id is None
    assert row.recommendation_policy == "projected_shortage_ceiling"
    assert row.recommendation_status == "reorder_recommended"
    assert row.forecast_method == "simple_mean"
    assert row.available_inventory == -5
    assert row.average_daily_demand == Decimal("4.25")


def test_approved_review_round_trip_preserves_decision() -> None:
    """An approved review reconstructs from review and decision rows."""
    review = make_approved_review()
    assert review.decision is not None

    review_row = recommendation_review_to_row(review)
    decision_row = recommendation_decision_to_row(
        review.recommendation_id,
        review.decision,
    )

    restored = recommendation_review_rows_to_domain(
        review_row,
        decision_row,
    )

    assert restored == review
    assert decision_row.decision_type == "approved"
    assert decision_row.approved_quantity == 36


def test_rejected_review_round_trip_preserves_reason() -> None:
    """A rejected review reconstructs with its normalized reason."""
    review = make_rejected_review()
    assert review.decision is not None

    review_row = recommendation_review_to_row(review)
    decision_row = recommendation_decision_to_row(
        review.recommendation_id,
        review.decision,
    )

    restored = recommendation_review_rows_to_domain(
        review_row,
        decision_row,
    )

    assert restored == review
    assert decision_row.decision_type == "rejected"
    assert decision_row.approved_quantity is None
    assert decision_row.note == "Supplier delivery is already confirmed"


def test_creation_event_round_trip_preserves_event() -> None:
    """A creation event survives conversion to and from its row."""
    event = create_review_created_audit_event(
        event_id=CREATION_EVENT_ID,
        review=make_pending_review(),
        sequence_number=1,
    )

    row = recommendation_audit_event_to_row(event)
    restored = recommendation_audit_event_row_to_domain(row)

    assert restored == event
    assert row.event_type == "review_created"
    assert row.occurred_at == CREATED_AT


def test_approval_event_round_trip_preserves_event() -> None:
    """An approval event survives conversion to and from its row."""
    event = create_review_decision_audit_event(
        event_id=APPROVAL_EVENT_ID,
        review=make_approved_review(),
        sequence_number=2,
    )

    row = recommendation_audit_event_to_row(event)
    restored = recommendation_audit_event_row_to_domain(row)

    assert restored == event
    assert row.event_type == "recommendation_approved"
    assert row.decision_id == APPROVAL_ID
    assert row.approved_quantity == 36


def test_rejection_event_round_trip_preserves_event() -> None:
    """A rejection event survives conversion to and from its row."""
    event = create_review_decision_audit_event(
        event_id=REJECTION_EVENT_ID,
        review=make_rejected_review(),
        sequence_number=2,
    )

    row = recommendation_audit_event_to_row(event)
    restored = recommendation_audit_event_row_to_domain(row)

    assert restored == event
    assert row.event_type == "recommendation_rejected"
    assert row.decision_id == REJECTION_ID
    assert row.approved_quantity is None


def test_terminal_review_requires_decision_row() -> None:
    """A terminal review cannot be reconstructed without its decision."""
    review_row = recommendation_review_to_row(make_approved_review())

    with pytest.raises(
        ValueError,
        match="review with decision_id requires a decision row",
    ):
        recommendation_review_rows_to_domain(review_row, None)


def test_pending_review_rejects_unexpected_decision_row() -> None:
    """A pending review cannot be paired with a terminal decision row."""
    approved = make_approved_review()
    assert approved.decision is not None

    pending_row = recommendation_review_to_row(make_pending_review())
    decision_row = recommendation_decision_to_row(
        approved.recommendation_id,
        approved.decision,
    )

    with pytest.raises(
        ValueError,
        match="review without decision_id must not include a decision row",
    ):
        recommendation_review_rows_to_domain(
            pending_row,
            decision_row,
        )


def test_review_rejects_decision_from_another_recommendation() -> None:
    """A decision row must belong to the reconstructed review."""
    review = make_approved_review()
    assert review.decision is not None

    review_row = recommendation_review_to_row(review)
    decision_row = recommendation_decision_to_row(
        review.recommendation_id,
        review.decision,
    )
    decision_row.recommendation_id = OTHER_RECOMMENDATION_ID

    with pytest.raises(
        ValueError,
        match=("decision recommendation_id must match review recommendation_id"),
    ):
        recommendation_review_rows_to_domain(
            review_row,
            decision_row,
        )


def test_review_rejects_wrong_decision_pointer() -> None:
    """A decision row ID must match the review's terminal pointer."""
    review = make_approved_review()
    assert review.decision is not None

    review_row = recommendation_review_to_row(review)
    decision_row = recommendation_decision_to_row(
        review.recommendation_id,
        review.decision,
    )
    decision_row.decision_id = OTHER_DECISION_ID

    with pytest.raises(
        ValueError,
        match="decision_id must match the review decision pointer",
    ):
        recommendation_review_rows_to_domain(
            review_row,
            decision_row,
        )
