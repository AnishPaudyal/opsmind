"""Tests for the isolated in-memory recommendation workflow repository."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from queue import Queue
from threading import Barrier, Thread
from uuid import UUID

import pytest

from opsmind.domain.errors import (
    DuplicateRecommendationReviewError,
    RecommendationReviewConflictError,
    RecommendationReviewNotFoundError,
)
from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.recommendation_review import (
    RecommendationReviewStatus,
    ReorderRecommendationReview,
    create_recommendation_review,
)
from opsmind.domain.reorder import (
    ReorderRecommendation,
    ReorderRecommendationPolicy,
    ReorderRecommendationStatus,
)
from opsmind.repositories.in_memory_recommendation_workflow import (
    InMemoryRecommendationWorkflowRepository,
)
from opsmind.repositories.recommendation_workflow import (
    RecommendationWorkflowRepository,
)

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")
RECOMMENDATION_ID = UUID("00000000-0000-0000-0000-000000000101")
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000201")
REJECTION_ID = UUID("00000000-0000-0000-0000-000000000202")
CREATED_AT = datetime(2026, 8, 1, 12, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 8, 1, 13, 0, tzinfo=UTC)


def make_review(
    recommendation_id: UUID = RECOMMENDATION_ID,
) -> ReorderRecommendationReview:
    """Build one pending actionable recommendation review."""
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
        recommendation_id=recommendation_id,
        recommendation=recommendation,
        created_at=CREATED_AT,
    )


def test_repository_satisfies_protocol_and_returns_same_immutable_review() -> None:
    repository: RecommendationWorkflowRepository = (
        InMemoryRecommendationWorkflowRepository()
    )
    review = make_review()

    stored = repository.create_review(review)

    assert stored is review
    assert repository.get_review(RECOMMENDATION_ID) is review


def test_duplicate_identifier_never_overwrites_existing_review() -> None:
    repository = InMemoryRecommendationWorkflowRepository()
    original = repository.create_review(make_review())

    with pytest.raises(DuplicateRecommendationReviewError):
        repository.create_review(make_review())

    assert repository.get_review(RECOMMENDATION_ID) is original


def test_missing_review_raises_typed_not_found_error() -> None:
    repository = InMemoryRecommendationWorkflowRepository()

    with pytest.raises(RecommendationReviewNotFoundError) as captured:
        repository.get_review(RECOMMENDATION_ID)

    assert captured.value.recommendation_id == RECOMMENDATION_ID


def test_approval_is_stored_atomically_and_identical_retry_is_idempotent() -> None:
    repository = InMemoryRecommendationWorkflowRepository()
    repository.create_review(make_review())

    approved = repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        note="Approved",
    )
    retried = repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=REJECTION_ID,
        decided_by=" Reviewer ",
        decided_at=DECIDED_AT + timedelta(days=1),
        approved_quantity=19,
        note=" Approved ",
    )

    assert retried is approved
    assert repository.get_review(RECOMMENDATION_ID) is approved
    assert approved.decision is not None
    assert approved.decision.decision_id == APPROVAL_ID
    assert approved.decision.decided_at == DECIDED_AT


def test_rejection_is_stored_atomically_and_identical_retry_is_idempotent() -> None:
    repository = InMemoryRecommendationWorkflowRepository()
    repository.create_review(make_review())

    rejected = repository.reject_review(
        RECOMMENDATION_ID,
        decision_id=REJECTION_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
        reason="Inbound",
    )
    retried = repository.reject_review(
        RECOMMENDATION_ID,
        decision_id=APPROVAL_ID,
        decided_by=" Reviewer ",
        decided_at=DECIDED_AT + timedelta(days=1),
        reason=" Inbound ",
    )

    assert retried is rejected
    assert repository.get_review(RECOMMENDATION_ID) is rejected
    assert rejected.decision is not None
    assert rejected.decision.decision_id == REJECTION_ID


def test_conflicting_retry_leaves_stored_state_unchanged() -> None:
    repository = InMemoryRecommendationWorkflowRepository()
    repository.create_review(make_review())
    approved = repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=APPROVAL_ID,
        decided_by="Reviewer",
        decided_at=DECIDED_AT,
    )

    with pytest.raises(RecommendationReviewConflictError):
        repository.reject_review(
            RECOMMENDATION_ID,
            decision_id=REJECTION_ID,
            decided_by="Reviewer",
            decided_at=DECIDED_AT,
            reason="Changed",
        )

    assert repository.get_review(RECOMMENDATION_ID) is approved


def test_separate_repository_instances_are_isolated() -> None:
    first = InMemoryRecommendationWorkflowRepository()
    second = InMemoryRecommendationWorkflowRepository()
    first.create_review(make_review())

    assert first.get_review(RECOMMENDATION_ID).recommendation_id == RECOMMENDATION_ID
    with pytest.raises(RecommendationReviewNotFoundError):
        second.get_review(RECOMMENDATION_ID)


def test_internal_mapping_has_no_public_exposure() -> None:
    repository = InMemoryRecommendationWorkflowRepository()

    assert not hasattr(repository, "reviews")
    assert not hasattr(repository, "recommendations")
    assert tuple(name for name in dir(repository) if not name.startswith("_")) == (
        "approve_review",
        "create_review",
        "get_review",
        "reject_review",
    )


def test_concurrent_approve_and_reject_have_exactly_one_winner() -> None:
    repository = InMemoryRecommendationWorkflowRepository()
    repository.create_review(make_review())
    barrier = Barrier(3)
    results: Queue[tuple[str, str]] = Queue()

    def approve_worker() -> None:
        barrier.wait()
        try:
            approved = repository.approve_review(
                RECOMMENDATION_ID,
                decision_id=APPROVAL_ID,
                decided_by="Approver",
                decided_at=DECIDED_AT,
            )
            results.put(("success", approved.review_status.value))
        except RecommendationReviewConflictError:
            results.put(("conflict", "approved"))

    def reject_worker() -> None:
        barrier.wait()
        try:
            rejected = repository.reject_review(
                RECOMMENDATION_ID,
                decision_id=REJECTION_ID,
                decided_by="Rejector",
                decided_at=DECIDED_AT,
                reason="No longer needed",
            )
            results.put(("success", rejected.review_status.value))
        except RecommendationReviewConflictError:
            results.put(("conflict", "rejected"))

    threads = [Thread(target=approve_worker), Thread(target=reject_worker)]
    for thread in threads:
        thread.start()
    barrier.wait()
    for thread in threads:
        thread.join()

    outcomes = [results.get_nowait(), results.get_nowait()]
    stored = repository.get_review(RECOMMENDATION_ID)

    assert sorted(item[0] for item in outcomes) == ["conflict", "success"]
    assert stored.review_status in {
        RecommendationReviewStatus.APPROVED,
        RecommendationReviewStatus.REJECTED,
    }
    assert [item for item in outcomes if item[0] == "success"] == [
        ("success", stored.review_status.value)
    ]
