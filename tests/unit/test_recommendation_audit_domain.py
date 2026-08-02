"""Tests for pure recommendation workflow audit events."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.recommendation_audit import (
    RecommendationAuditEvent,
    RecommendationAuditEventType,
    create_review_created_audit_event,
    create_review_decision_audit_event,
)
from opsmind.domain.recommendation_review import (
    RecommendationReviewStatus,
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

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")
RECOMMENDATION_ID = UUID("00000000-0000-0000-0000-000000000101")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000201")
EVENT_ID = UUID("00000000-0000-0000-0000-000000000301")
CREATED_AT = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)


def make_pending_review() -> ReorderRecommendationReview:
    """Create a deterministic actionable review."""
    recommendation = ReorderRecommendation(
        product_id=PRODUCT_ID,
        unit_of_measure="units",
        recommendation_policy=(ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING),
        recommendation_status=ReorderRecommendationStatus.REORDER_RECOMMENDED,
        forecast_method=ForecastMethod.SIMPLE_MEAN,
        as_of_date=date(2026, 7, 4),
        lookback_observations_requested=4,
        observations_used=4,
        training_start_date=date(2026, 7, 1),
        training_end_date=date(2026, 7, 4),
        average_daily_demand=Decimal("9.75"),
        lead_time_days=5,
        on_hand_quantity=40,
        allocated_quantity=10,
        available_inventory=30,
        forecasted_lead_time_demand=Decimal("48.75"),
        projected_inventory_balance=Decimal("-18.75"),
        projected_shortage_quantity=Decimal("18.75"),
        recommended_reorder_quantity=19,
    )
    return create_recommendation_review(
        recommendation_id=RECOMMENDATION_ID,
        recommendation=recommendation,
        created_at=CREATED_AT,
    )


def make_creation_event() -> RecommendationAuditEvent:
    """Create the standard first audit event."""
    return create_review_created_audit_event(
        event_id=EVENT_ID,
        review=make_pending_review(),
        sequence_number=1,
    )


def test_event_type_enum_contains_exactly_the_supported_events() -> None:
    assert tuple(RecommendationAuditEventType) == (
        RecommendationAuditEventType.REVIEW_CREATED,
        RecommendationAuditEventType.RECOMMENDATION_APPROVED,
        RecommendationAuditEventType.RECOMMENDATION_REJECTED,
    )


def test_creation_event_is_frozen_slotted_deterministic_and_complete() -> None:
    review = make_pending_review()
    original_review = review

    event = create_review_created_audit_event(
        event_id=EVENT_ID,
        review=review,
        sequence_number=1,
    )
    repeated = create_review_created_audit_event(
        event_id=EVENT_ID,
        review=review,
        sequence_number=1,
    )

    assert event == repeated
    assert event.event_id == EVENT_ID
    assert event.recommendation_id == RECOMMENDATION_ID
    assert event.sequence_number == 1
    assert event.event_type is RecommendationAuditEventType.REVIEW_CREATED
    assert event.occurred_at == CREATED_AT
    assert event.review_status is RecommendationReviewStatus.PENDING_REVIEW
    assert event.decision_id is None
    assert event.actor is None
    assert event.recommended_reorder_quantity == 19
    assert event.approved_quantity is None
    assert event.note is None
    assert review is original_review
    assert not hasattr(event, "__dict__")
    with pytest.raises(FrozenInstanceError):
        event.sequence_number = 2  # type: ignore[misc]


@pytest.mark.parametrize("sequence_number", [0, -1, True])
def test_event_requires_positive_non_boolean_sequence(sequence_number: int) -> None:
    with pytest.raises(ValueError, match="sequence_number must be a positive integer"):
        replace(make_creation_event(), sequence_number=sequence_number)


@pytest.mark.parametrize("quantity", [0, -1, True])
def test_event_requires_positive_recommended_quantity(quantity: int) -> None:
    with pytest.raises(
        ValueError,
        match="recommended_reorder_quantity must be a positive integer",
    ):
        replace(make_creation_event(), recommended_reorder_quantity=quantity)


def test_event_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="occurred_at must be timezone-aware"):
        replace(
            make_creation_event(),
            occurred_at=datetime(2026, 8, 1, 12, 0),
        )


def test_event_normalizes_aware_timestamp_to_utc() -> None:
    central = timezone(timedelta(hours=-5))

    event = replace(
        make_creation_event(),
        occurred_at=datetime(2026, 8, 1, 7, 0, tzinfo=central),
    )

    assert event.occurred_at == CREATED_AT
    assert event.occurred_at.tzinfo is UTC


@pytest.mark.parametrize("terminal_status", ["approved", "rejected"])
def test_creation_factory_rejects_terminal_review(terminal_status: str) -> None:
    pending = make_pending_review()
    if terminal_status == "approved":
        terminal = approve_recommendation(
            review=pending,
            decision_id=DECISION_ID,
            decided_by="Reviewer",
            decided_at=DECIDED_AT,
        )
    else:
        terminal = reject_recommendation(
            review=pending,
            decision_id=DECISION_ID,
            decided_by="Reviewer",
            decided_at=DECIDED_AT,
            reason="Inbound scheduled",
        )

    with pytest.raises(ValueError, match="requires a pending review"):
        create_review_created_audit_event(
            event_id=EVENT_ID,
            review=terminal,
            sequence_number=1,
        )


def test_approval_event_uses_stored_normalized_decision_facts() -> None:
    pending = make_pending_review()
    approved = approve_recommendation(
        review=pending,
        decision_id=DECISION_ID,
        decided_by=" Reviewer ",
        decided_at=DECIDED_AT,
        approved_quantity=24,
        note=" Case pack ",
    )

    event = create_review_decision_audit_event(
        event_id=EVENT_ID,
        review=approved,
        sequence_number=2,
    )

    assert event.event_type is RecommendationAuditEventType.RECOMMENDATION_APPROVED
    assert event.review_status is RecommendationReviewStatus.APPROVED
    assert event.decision_id == DECISION_ID
    assert event.actor == "Reviewer"
    assert event.recommended_reorder_quantity == 19
    assert event.approved_quantity == 24
    assert event.note == "Case pack"
    assert event.occurred_at == DECIDED_AT
    assert approved.recommendation is pending.recommendation


def test_rejection_event_uses_stored_normalized_decision_facts() -> None:
    rejected = reject_recommendation(
        review=make_pending_review(),
        decision_id=DECISION_ID,
        decided_by=" Reviewer ",
        decided_at=DECIDED_AT,
        reason=" Inbound scheduled ",
    )

    event = create_review_decision_audit_event(
        event_id=EVENT_ID,
        review=rejected,
        sequence_number=2,
    )

    assert event.event_type is RecommendationAuditEventType.RECOMMENDATION_REJECTED
    assert event.review_status is RecommendationReviewStatus.REJECTED
    assert event.decision_id == DECISION_ID
    assert event.actor == "Reviewer"
    assert event.recommended_reorder_quantity == 19
    assert event.approved_quantity is None
    assert event.note == "Inbound scheduled"
    assert event.occurred_at == DECIDED_AT


def test_decision_factory_rejects_pending_review() -> None:
    with pytest.raises(ValueError, match="requires a terminal review"):
        create_review_decision_audit_event(
            event_id=EVENT_ID,
            review=make_pending_review(),
            sequence_number=2,
        )


def test_event_type_specific_invariants_reject_invalid_combinations() -> None:
    creation = make_creation_event()

    with pytest.raises(ValueError, match="sequence_number 1"):
        replace(creation, sequence_number=2)
    with pytest.raises(ValueError, match="must not contain decision details"):
        replace(creation, actor="Reviewer")

    approved = approve_recommendation(
        review=make_pending_review(),
        decision_id=DECISION_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
    )
    approval_event = create_review_decision_audit_event(
        event_id=EVENT_ID,
        review=approved,
        sequence_number=2,
    )
    with pytest.raises(ValueError, match="requires approved_quantity"):
        replace(approval_event, approved_quantity=None)

    rejected = reject_recommendation(
        review=make_pending_review(),
        decision_id=DECISION_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        reason="No",
    )
    rejection_event = create_review_decision_audit_event(
        event_id=EVENT_ID,
        review=rejected,
        sequence_number=2,
    )
    with pytest.raises(ValueError, match="requires decision details"):
        replace(rejection_event, note=" ")
