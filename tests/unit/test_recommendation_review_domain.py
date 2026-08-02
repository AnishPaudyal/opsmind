"""Tests for pure reorder-recommendation review transitions."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from opsmind.core.clock import SystemClock
from opsmind.domain.errors import (
    NoActionableReorderRecommendationError,
    RecommendationReviewConflictError,
)
from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.recommendation_review import (
    RecommendationDecision,
    RecommendationDecisionType,
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
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000201")
RETRY_ID = UUID("00000000-0000-0000-0000-000000000202")
CREATED_AT = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)


def make_recommendation(
    *,
    quantity: int = 19,
    status: ReorderRecommendationStatus = (
        ReorderRecommendationStatus.REORDER_RECOMMENDED
    ),
) -> ReorderRecommendation:
    """Build deterministic recommendation evidence for domain tests."""
    return ReorderRecommendation(
        product_id=PRODUCT_ID,
        unit_of_measure="units",
        recommendation_policy=(ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING),
        recommendation_status=status,
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
        recommended_reorder_quantity=quantity,
    )


def make_pending_review() -> ReorderRecommendationReview:
    """Create the standard pending review."""
    return create_recommendation_review(
        recommendation_id=RECOMMENDATION_ID,
        recommendation=make_recommendation(),
        created_at=CREATED_AT,
    )


def test_create_review_stores_actionable_snapshot_as_pending() -> None:
    recommendation = make_recommendation()

    review = create_recommendation_review(
        recommendation_id=RECOMMENDATION_ID,
        recommendation=recommendation,
        created_at=CREATED_AT,
    )

    assert review.recommendation_id == RECOMMENDATION_ID
    assert review.recommendation is recommendation
    assert review.review_status is RecommendationReviewStatus.PENDING_REVIEW
    assert review.created_at == CREATED_AT
    assert review.decision is None


@pytest.mark.parametrize(
    ("quantity", "recommendation_status"),
    [
        (0, ReorderRecommendationStatus.NO_REORDER_NEEDED),
        (0, ReorderRecommendationStatus.REORDER_RECOMMENDED),
        (19, ReorderRecommendationStatus.NO_REORDER_NEEDED),
    ],
)
def test_create_review_rejects_non_actionable_recommendations(
    quantity: int,
    recommendation_status: ReorderRecommendationStatus,
) -> None:
    with pytest.raises(NoActionableReorderRecommendationError):
        create_recommendation_review(
            recommendation_id=RECOMMENDATION_ID,
            recommendation=make_recommendation(
                quantity=quantity,
                status=recommendation_status,
            ),
            created_at=CREATED_AT,
        )


def test_models_are_frozen_and_slotted() -> None:
    review = make_pending_review()

    with pytest.raises(FrozenInstanceError):
        review.review_status = RecommendationReviewStatus.APPROVED  # type: ignore[misc]
    assert not hasattr(review, "__dict__")


def test_approve_defaults_to_recommended_quantity_and_normalizes_text() -> None:
    review = make_pending_review()

    approved = approve_recommendation(
        review=review,
        decision_id=APPROVAL_ID,
        decided_by="  Anish Paudyal  ",
        decided_at=DECIDED_AT,
        note="  Approved as recommended.  ",
    )

    assert approved is not review
    assert approved.recommendation is review.recommendation
    assert approved.review_status is RecommendationReviewStatus.APPROVED
    assert approved.decision == RecommendationDecision(
        decision_id=APPROVAL_ID,
        decision_type=RecommendationDecisionType.APPROVED,
        decided_by="Anish Paudyal",
        decided_at=DECIDED_AT,
        approved_quantity=19,
        note="Approved as recommended.",
    )


def test_approve_preserves_distinct_human_quantity() -> None:
    approved = approve_recommendation(
        review=make_pending_review(),
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        approved_quantity=24,
        note="Case pack",
    )

    assert approved.recommendation.recommended_reorder_quantity == 19
    assert approved.decision is not None
    assert approved.decision.approved_quantity == 24


def test_identical_approval_retry_returns_same_object_and_original_metadata() -> None:
    approved = approve_recommendation(
        review=make_pending_review(),
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        note="   ",
    )

    retried = approve_recommendation(
        review=approved,
        decision_id=RETRY_ID,
        decided_by=" Reviewer ",
        decided_at=DECIDED_AT + timedelta(days=1),
        approved_quantity=19,
        note=None,
    )

    assert retried is approved
    assert retried.decision is not None
    assert retried.decision.decision_id == APPROVAL_ID
    assert retried.decision.decided_at == DECIDED_AT


@pytest.mark.parametrize(
    ("actor", "quantity", "note"),
    [
        ("Other reviewer", 19, "Approved"),
        ("Reviewer", 20, "Approved"),
        ("Reviewer", 19, "Different"),
    ],
)
def test_different_approval_retry_conflicts_without_mutating_state(
    actor: str,
    quantity: int,
    note: str,
) -> None:
    approved = approve_recommendation(
        review=make_pending_review(),
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        approved_quantity=19,
        note="Approved",
    )

    with pytest.raises(RecommendationReviewConflictError):
        approve_recommendation(
            review=approved,
            decision_id=RETRY_ID,
            decided_by=actor,
            decided_at=DECIDED_AT,
            approved_quantity=quantity,
            note=note,
        )
    assert approved.decision is not None
    assert approved.decision.decision_id == APPROVAL_ID


def test_reject_normalizes_required_reason_and_has_no_quantity() -> None:
    rejected = reject_recommendation(
        review=make_pending_review(),
        decision_id=APPROVAL_ID,
        decided_by=" Reviewer ",
        decided_at=DECIDED_AT,
        reason=" Inbound inventory is scheduled. ",
    )

    assert rejected.review_status is RecommendationReviewStatus.REJECTED
    assert rejected.decision is not None
    assert rejected.decision.decision_type is RecommendationDecisionType.REJECTED
    assert rejected.decision.decided_by == "Reviewer"
    assert rejected.decision.approved_quantity is None
    assert rejected.decision.note == "Inbound inventory is scheduled."


def test_identical_rejection_retry_returns_same_object() -> None:
    rejected = reject_recommendation(
        review=make_pending_review(),
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        reason="Inbound",
    )

    retried = reject_recommendation(
        review=rejected,
        decision_id=RETRY_ID,
        decided_by=" Reviewer ",
        decided_at=DECIDED_AT + timedelta(hours=1),
        reason=" Inbound ",
    )

    assert retried is rejected


@pytest.mark.parametrize(
    ("actor", "reason"),
    [("Other", "Inbound"), ("Reviewer", "Different")],
)
def test_different_rejection_retry_conflicts(actor: str, reason: str) -> None:
    rejected = reject_recommendation(
        review=make_pending_review(),
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        reason="Inbound",
    )

    with pytest.raises(RecommendationReviewConflictError):
        reject_recommendation(
            review=rejected,
            decision_id=RETRY_ID,
            decided_by=actor,
            decided_at=DECIDED_AT,
            reason=reason,
        )


def test_cross_decision_retries_always_conflict() -> None:
    pending = make_pending_review()
    approved = approve_recommendation(
        review=pending,
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
    )
    rejected = reject_recommendation(
        review=pending,
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        reason="No",
    )

    with pytest.raises(RecommendationReviewConflictError):
        reject_recommendation(
            review=approved,
            decision_id=RETRY_ID,
            decided_by="Reviewer",
            decided_at=DECIDED_AT,
            reason="No",
        )
    with pytest.raises(RecommendationReviewConflictError):
        approve_recommendation(
            review=rejected,
            decision_id=RETRY_ID,
            decided_by="Reviewer",
            decided_at=DECIDED_AT,
        )


@pytest.mark.parametrize("quantity", [0, -1, True])
def test_approval_rejects_non_positive_or_boolean_quantity(
    quantity: int,
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        approve_recommendation(
            review=make_pending_review(),
            decision_id=APPROVAL_ID,
            decided_by="Reviewer",
            decided_at=DECIDED_AT,
            approved_quantity=quantity,
        )


@pytest.mark.parametrize("field", ["created_at", "decided_at"])
def test_workflow_rejects_naive_timestamps(field: str) -> None:
    naive = datetime(2026, 8, 1, 12, 0)
    if field == "created_at":
        with pytest.raises(ValueError, match="timezone-aware"):
            create_recommendation_review(
                recommendation_id=RECOMMENDATION_ID,
                recommendation=make_recommendation(),
                created_at=naive,
            )
        return

    with pytest.raises(ValueError, match="timezone-aware"):
        approve_recommendation(
            review=make_pending_review(),
            decision_id=APPROVAL_ID,
            decided_by="Reviewer",
            decided_at=naive,
        )


def test_aware_non_utc_timestamps_are_normalized_to_utc() -> None:
    central = timezone(timedelta(hours=-5))
    created = datetime(2026, 8, 1, 7, 0, tzinfo=central)
    decided = datetime(2026, 8, 1, 8, 0, tzinfo=central)

    review = create_recommendation_review(
        recommendation_id=RECOMMENDATION_ID,
        recommendation=make_recommendation(),
        created_at=created,
    )
    approved = approve_recommendation(
        review=review,
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=decided,
    )

    assert review.created_at == CREATED_AT
    assert approved.decision is not None
    assert approved.decision.decided_at == DECIDED_AT
    assert approved.decision.decided_at.tzinfo is UTC


def test_direct_aggregate_construction_enforces_state_invariants() -> None:
    decision = RecommendationDecision(
        decision_id=APPROVAL_ID,
        decision_type=RecommendationDecisionType.APPROVED,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        approved_quantity=19,
        note=None,
    )

    with pytest.raises(ValueError, match="pending reviews"):
        replace(make_pending_review(), decision=decision)
    with pytest.raises(ValueError, match="terminal reviews"):
        replace(
            make_pending_review(),
            review_status=RecommendationReviewStatus.APPROVED,
        )
    with pytest.raises(ValueError, match="must match"):
        replace(
            make_pending_review(),
            review_status=RecommendationReviewStatus.REJECTED,
            decision=decision,
        )


def test_system_clock_returns_an_aware_utc_datetime() -> None:
    current = SystemClock().now()

    assert current.tzinfo is UTC
    assert current.utcoffset() == timedelta(0)
