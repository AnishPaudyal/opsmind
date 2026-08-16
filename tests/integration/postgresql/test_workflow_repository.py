"""Real-PostgreSQL recommendation workflow repository tests."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from queue import Queue
from threading import Barrier, Thread
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from opsmind.domain.errors import (
    DuplicateRecommendationReviewError,
    RecommendationReviewConflictError,
    RecommendationReviewNotFoundError,
)
from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.recommendation_audit import (
    RecommendationAuditEvent,
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
from opsmind.persistence.postgresql.database import SessionFactory
from opsmind.persistence.postgresql.mappings import (
    recommendation_audit_event_to_row,
    recommendation_decision_to_row,
    recommendation_review_to_row,
)
from opsmind.persistence.postgresql.models import (
    ProductRow,
    RecommendationAuditEventRow,
    RecommendationDecisionRow,
)
from opsmind.persistence.postgresql.workflow_repository import (
    PostgresRecommendationWorkflowRepository,
)

PRODUCT_ID = UUID("90000000-0000-0000-0000-000000000001")
RECOMMENDATION_ID = UUID("91000000-0000-0000-0000-000000000001")
SECOND_RECOMMENDATION_ID = UUID("91000000-0000-0000-0000-000000000002")
MISSING_RECOMMENDATION_ID = UUID("91000000-0000-0000-0000-000000000099")
DECISION_ID = UUID("92000000-0000-0000-0000-000000000001")
CREATION_EVENT_ID = UUID("93000000-0000-0000-0000-000000000001")
DECISION_EVENT_ID = UUID("93000000-0000-0000-0000-000000000002")
SECOND_CREATION_EVENT_ID = UUID("93000000-0000-0000-0000-000000000003")
RETRY_DECISION_ID = UUID("92000000-0000-0000-0000-000000000002")
RETRY_EVENT_ID = UUID("93000000-0000-0000-0000-000000000004")
REJECTION_DECISION_ID = UUID("92000000-0000-0000-0000-000000000003")
REJECTION_EVENT_ID = UUID("93000000-0000-0000-0000-000000000005")

CREATED_AT = datetime(2026, 8, 4, 15, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 8, 4, 16, 0, tzinfo=UTC)


def make_recommendation() -> ReorderRecommendation:
    """Build one complete actionable recommendation snapshot."""
    return ReorderRecommendation(
        product_id=PRODUCT_ID,
        unit_of_measure="units",
        recommendation_policy=(ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING),
        recommendation_status=(ReorderRecommendationStatus.REORDER_RECOMMENDED),
        forecast_method=ForecastMethod.SIMPLE_MEAN,
        as_of_date=date(2026, 8, 4),
        lookback_observations_requested=30,
        observations_used=30,
        training_start_date=date(2026, 7, 6),
        training_end_date=date(2026, 8, 4),
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


def make_pending_review(
    recommendation_id: UUID = RECOMMENDATION_ID,
    *,
    created_at: datetime = CREATED_AT,
) -> ReorderRecommendationReview:
    """Build one valid pending review."""
    return create_recommendation_review(
        recommendation_id=recommendation_id,
        recommendation=make_recommendation(),
        created_at=created_at,
    )


def make_approved_review() -> ReorderRecommendationReview:
    """Build one valid approved review."""
    return approve_recommendation(
        review=make_pending_review(),
        decision_id=DECISION_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        approved_quantity=36,
        note="Expedite replenishment",
    )


def make_creation_event(
    review: ReorderRecommendationReview | None = None,
    *,
    event_id: UUID = CREATION_EVENT_ID,
) -> RecommendationAuditEvent:
    """Build the required sequence-one creation event."""
    resolved_review = make_pending_review() if review is None else review
    return create_review_created_audit_event(
        event_id=event_id,
        review=resolved_review,
        sequence_number=1,
    )


def make_decision_event(
    review: ReorderRecommendationReview | None = None,
    *,
    event_id: UUID = DECISION_EVENT_ID,
) -> RecommendationAuditEvent:
    """Build a sequence-two terminal decision event."""
    resolved_review = make_approved_review() if review is None else review
    return create_review_decision_audit_event(
        event_id=event_id,
        review=resolved_review,
        sequence_number=2,
    )


def persist_product(session: Session) -> None:
    """Insert the product required by the review foreign key."""
    session.add(
        ProductRow(
            id=PRODUCT_ID,
            sku="WORKFLOW-READ-001",
            name="Workflow Read Test Product",
            unit_of_measure="units",
            lead_time_days=7,
            is_active=True,
        )
    )
    session.flush()


def persist_workflow(
    session: Session,
    review: ReorderRecommendationReview,
    events: tuple[RecommendationAuditEvent, ...],
) -> None:
    """Persist one pending or terminal workflow in dependency-safe order."""
    persist_product(session)

    if review.decision is None:
        session.add(recommendation_review_to_row(review))
        session.flush()
    else:
        pending_review = make_pending_review()
        review_row = recommendation_review_to_row(pending_review)
        session.add(review_row)
        session.flush()

        decision = review.decision
        session.add(
            recommendation_decision_to_row(
                review.recommendation_id,
                decision,
            )
        )
        session.flush()

        review_row.review_status = review.review_status.value
        review_row.decision_id = decision.decision_id
        session.flush()

    session.add_all(recommendation_audit_event_to_row(event) for event in events)
    session.commit()


def make_repository(
    session_factory: SessionFactory,
) -> PostgresRecommendationWorkflowRepository:
    """Return one workflow repository over the shared test database."""
    return PostgresRecommendationWorkflowRepository(session_factory)


def create_pending_workflow(
    session_factory: SessionFactory,
    repository: PostgresRecommendationWorkflowRepository,
    review: ReorderRecommendationReview | None = None,
    *,
    event_id: UUID = CREATION_EVENT_ID,
) -> ReorderRecommendationReview:
    """Persist the product and one pending workflow."""
    resolved_review = make_pending_review() if review is None else review
    with session_factory() as session:
        persist_product(session)
        session.commit()

    return repository.create_review(
        resolved_review,
        event_id=event_id,
    )


def test_get_review_returns_complete_pending_snapshot_across_instances(
    session_factory: SessionFactory,
) -> None:
    """Separate repository instances reconstruct the same durable review."""
    expected = make_pending_review()

    with session_factory() as session:
        persist_workflow(
            session,
            expected,
            (make_creation_event(),),
        )

    first = make_repository(session_factory).get_review(RECOMMENDATION_ID)
    second = make_repository(session_factory).get_review(RECOMMENDATION_ID)

    assert first == expected
    assert second == expected
    assert first is not expected
    assert second is not first


def test_list_reviews_persists_filters_and_newest_first_order(
    session_factory: SessionFactory,
) -> None:
    repository = make_repository(session_factory)
    first = create_pending_workflow(session_factory, repository)
    approved = repository.approve_review(
        first.recommendation_id,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        approved_quantity=None,
        note=None,
    )
    second = make_pending_review(
        SECOND_RECOMMENDATION_ID,
        created_at=CREATED_AT + timedelta(hours=1),
    )
    repository.create_review(second, event_id=SECOND_CREATION_EVENT_ID)

    restarted = make_repository(session_factory)
    assert restarted.list_reviews() == (second, approved)
    assert restarted.list_reviews(
        product_id=PRODUCT_ID,
        review_status=RecommendationReviewStatus.APPROVED,
    ) == (approved,)
    assert (
        restarted.list_reviews(review_status=RecommendationReviewStatus.REJECTED) == ()
    )


def test_get_review_reconstructs_terminal_decision(
    session_factory: SessionFactory,
) -> None:
    """A terminal aggregate includes its detached immutable decision."""
    expected = make_approved_review()

    with session_factory() as session:
        persist_workflow(
            session,
            expected,
            (make_creation_event(), make_decision_event()),
        )

    stored = make_repository(session_factory).get_review(RECOMMENDATION_ID)

    assert stored == expected
    assert stored.decision == expected.decision


def test_audit_events_are_returned_in_sequence_order(
    session_factory: SessionFactory,
) -> None:
    """Database insertion order does not control public history order."""
    review = make_approved_review()
    creation_event = make_creation_event()
    decision_event = make_decision_event()

    with session_factory() as session:
        persist_workflow(
            session,
            review,
            (decision_event, creation_event),
        )

    events = make_repository(session_factory).list_audit_events(RECOMMENDATION_ID)

    assert events == (creation_event, decision_event)
    assert tuple(event.sequence_number for event in events) == (1, 2)


def test_missing_review_raises_typed_error_for_both_reads(
    session_factory: SessionFactory,
) -> None:
    """Review and audit reads share the existing not-found contract."""
    repository = make_repository(session_factory)

    with pytest.raises(
        RecommendationReviewNotFoundError,
    ) as review_error:
        repository.get_review(MISSING_RECOMMENDATION_ID)

    with pytest.raises(
        RecommendationReviewNotFoundError,
    ) as history_error:
        repository.list_audit_events(MISSING_RECOMMENDATION_ID)

    assert review_error.value.recommendation_id == MISSING_RECOMMENDATION_ID
    assert history_error.value.recommendation_id == MISSING_RECOMMENDATION_ID


def test_missing_persisted_history_is_detected(
    session_factory: SessionFactory,
) -> None:
    """A review without its required creation event is an internal failure."""
    review = make_pending_review()

    with session_factory() as session:
        persist_workflow(session, review, ())

    repository = make_repository(session_factory)

    with pytest.raises(
        RuntimeError,
        match="audit history must not be empty",
    ):
        repository.list_audit_events(RECOMMENDATION_ID)


def test_create_review_persists_review_and_creation_event_atomically(
    session_factory: SessionFactory,
) -> None:
    """Creation is durable and observable through another repository."""
    expected = make_pending_review()

    with session_factory() as session:
        persist_product(session)
        session.commit()

    stored = make_repository(session_factory).create_review(
        expected,
        event_id=CREATION_EVENT_ID,
    )

    second_repository = make_repository(session_factory)

    assert stored is expected
    assert second_repository.get_review(RECOMMENDATION_ID) == expected
    assert second_repository.list_audit_events(RECOMMENDATION_ID) == (
        make_creation_event(),
    )


def test_duplicate_review_is_translated_without_overwriting_state(
    session_factory: SessionFactory,
) -> None:
    """Duplicate recommendation IDs preserve the first complete workflow."""
    original = make_pending_review()
    repository = make_repository(session_factory)

    with session_factory() as session:
        persist_product(session)
        session.commit()

    repository.create_review(
        original,
        event_id=CREATION_EVENT_ID,
    )

    with pytest.raises(
        DuplicateRecommendationReviewError,
    ) as error:
        repository.create_review(
            make_pending_review(),
            event_id=DECISION_EVENT_ID,
        )

    assert error.value.recommendation_id == RECOMMENDATION_ID
    assert repository.get_review(RECOMMENDATION_ID) == original
    assert repository.list_audit_events(RECOMMENDATION_ID) == (make_creation_event(),)


def test_invalid_creation_event_stores_no_review(
    session_factory: SessionFactory,
) -> None:
    """Domain event validation occurs before any database mutation."""
    repository = make_repository(session_factory)

    with pytest.raises(
        ValueError,
        match="creation event requires a pending review",
    ):
        repository.create_review(
            make_approved_review(),
            event_id=CREATION_EVENT_ID,
        )

    with pytest.raises(RecommendationReviewNotFoundError):
        repository.get_review(RECOMMENDATION_ID)


def test_creation_event_failure_rolls_back_inserted_review(
    session_factory: SessionFactory,
) -> None:
    """A later event constraint failure removes the earlier review insert."""
    repository = make_repository(session_factory)

    with session_factory() as session:
        persist_product(session)
        session.commit()

    repository.create_review(
        make_pending_review(),
        event_id=CREATION_EVENT_ID,
    )

    second_review = create_recommendation_review(
        recommendation_id=SECOND_RECOMMENDATION_ID,
        recommendation=make_recommendation(),
        created_at=CREATED_AT,
    )

    with pytest.raises(IntegrityError):
        repository.create_review(
            second_review,
            event_id=CREATION_EVENT_ID,
        )

    with pytest.raises(RecommendationReviewNotFoundError):
        repository.get_review(SECOND_RECOMMENDATION_ID)

    assert repository.get_review(RECOMMENDATION_ID) == make_pending_review()
    assert repository.list_audit_events(RECOMMENDATION_ID) == (make_creation_event(),)


def test_approval_persists_default_quantity_and_terminal_event(
    session_factory: SessionFactory,
) -> None:
    """Approval stores one complete terminal aggregate and event."""
    repository = make_repository(session_factory)
    pending = create_pending_workflow(
        session_factory,
        repository,
    )

    stored = repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by=" planner@example.com ",
        decided_at=DECIDED_AT,
        approved_quantity=None,
        note=" Expedite replenishment ",
    )
    expected = approve_recommendation(
        review=pending,
        decision_id=DECISION_ID,
        decided_by=" planner@example.com ",
        decided_at=DECIDED_AT,
        approved_quantity=None,
        note=" Expedite replenishment ",
    )

    assert stored == expected
    assert stored.decision is not None
    assert stored.decision.approved_quantity == 35
    assert repository.get_review(RECOMMENDATION_ID) == expected
    assert repository.list_audit_events(RECOMMENDATION_ID) == (
        make_creation_event(pending),
        make_decision_event(expected),
    )


def test_identical_approval_retry_ignores_candidate_identity(
    session_factory: SessionFactory,
) -> None:
    """An equivalent approval retry inserts and changes nothing."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    first = repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by=" planner@example.com ",
        decided_at=DECIDED_AT,
        approved_quantity=None,
        note=" Expedite replenishment ",
    )
    original_history = repository.list_audit_events(RECOMMENDATION_ID)

    retried = repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=RETRY_DECISION_ID,
        event_id=RETRY_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT + timedelta(hours=2),
        approved_quantity=35,
        note="Expedite replenishment",
    )

    assert retried == first
    assert retried.decision is not None
    assert retried.decision.decision_id == DECISION_ID
    assert retried.decision.decided_at == DECIDED_AT
    assert repository.list_audit_events(RECOMMENDATION_ID) == original_history


def test_changed_approval_retry_conflicts_without_mutation(
    session_factory: SessionFactory,
) -> None:
    """A materially changed approval leaves stored state untouched."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    first = repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        approved_quantity=35,
        note="Expedite replenishment",
    )
    original_history = repository.list_audit_events(RECOMMENDATION_ID)

    with pytest.raises(RecommendationReviewConflictError):
        repository.approve_review(
            RECOMMENDATION_ID,
            decision_id=RETRY_DECISION_ID,
            event_id=RETRY_EVENT_ID,
            decided_by="planner@example.com",
            decided_at=DECIDED_AT + timedelta(hours=2),
            approved_quantity=36,
            note="Expedite replenishment",
        )

    assert repository.get_review(RECOMMENDATION_ID) == first
    assert repository.list_audit_events(RECOMMENDATION_ID) == original_history


def test_rejection_persists_and_identical_retry_is_idempotent(
    session_factory: SessionFactory,
) -> None:
    """Rejection persists once and ignores equivalent retry identity."""
    repository = make_repository(session_factory)
    pending = create_pending_workflow(
        session_factory,
        repository,
    )

    first = repository.reject_review(
        RECOMMENDATION_ID,
        decision_id=REJECTION_DECISION_ID,
        event_id=REJECTION_EVENT_ID,
        decided_by=" planner@example.com ",
        decided_at=DECIDED_AT,
        reason=" Supplier delivery is already confirmed ",
    )
    expected = reject_recommendation(
        review=pending,
        decision_id=REJECTION_DECISION_ID,
        decided_by=" planner@example.com ",
        decided_at=DECIDED_AT,
        reason=" Supplier delivery is already confirmed ",
    )
    original_history = repository.list_audit_events(RECOMMENDATION_ID)

    retried = repository.reject_review(
        RECOMMENDATION_ID,
        decision_id=RETRY_DECISION_ID,
        event_id=RETRY_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT + timedelta(hours=3),
        reason="Supplier delivery is already confirmed",
    )

    assert first == expected
    assert retried == first
    assert retried.decision is not None
    assert retried.decision.decision_id == REJECTION_DECISION_ID
    assert repository.get_review(RECOMMENDATION_ID) == expected
    assert original_history == (
        make_creation_event(pending),
        make_decision_event(
            expected,
            event_id=REJECTION_EVENT_ID,
        ),
    )
    assert repository.list_audit_events(RECOMMENDATION_ID) == original_history


def test_changed_rejection_retry_conflicts_without_mutation(
    session_factory: SessionFactory,
) -> None:
    """A changed rejection reason preserves the first decision."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    first = repository.reject_review(
        RECOMMENDATION_ID,
        decision_id=REJECTION_DECISION_ID,
        event_id=REJECTION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        reason="Supplier delivery is already confirmed",
    )
    original_history = repository.list_audit_events(RECOMMENDATION_ID)

    with pytest.raises(RecommendationReviewConflictError):
        repository.reject_review(
            RECOMMENDATION_ID,
            decision_id=RETRY_DECISION_ID,
            event_id=RETRY_EVENT_ID,
            decided_by="planner@example.com",
            decided_at=DECIDED_AT + timedelta(hours=3),
            reason="Demand was entered incorrectly",
        )

    assert repository.get_review(RECOMMENDATION_ID) == first
    assert repository.list_audit_events(RECOMMENDATION_ID) == original_history


def test_opposite_terminal_retry_conflicts_without_mutation(
    session_factory: SessionFactory,
) -> None:
    """A rejected transition cannot replace an approved transition."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    approved = repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
    )
    original_history = repository.list_audit_events(RECOMMENDATION_ID)

    with pytest.raises(RecommendationReviewConflictError):
        repository.reject_review(
            RECOMMENDATION_ID,
            decision_id=REJECTION_DECISION_ID,
            event_id=REJECTION_EVENT_ID,
            decided_by="planner@example.com",
            decided_at=DECIDED_AT + timedelta(hours=1),
            reason="Do not replenish",
        )

    assert repository.get_review(RECOMMENDATION_ID) == approved
    assert repository.list_audit_events(RECOMMENDATION_ID) == original_history


def test_terminal_methods_preserve_typed_missing_error(
    session_factory: SessionFactory,
) -> None:
    """Both transition methods preserve the protocol's not-found error."""
    repository = make_repository(session_factory)

    with pytest.raises(RecommendationReviewNotFoundError):
        repository.approve_review(
            MISSING_RECOMMENDATION_ID,
            decision_id=DECISION_ID,
            event_id=DECISION_EVENT_ID,
            decided_by="planner@example.com",
            decided_at=DECIDED_AT,
        )

    with pytest.raises(RecommendationReviewNotFoundError):
        repository.reject_review(
            MISSING_RECOMMENDATION_ID,
            decision_id=REJECTION_DECISION_ID,
            event_id=REJECTION_EVENT_ID,
            decided_by="planner@example.com",
            decided_at=DECIDED_AT,
            reason="Do not replenish",
        )


def test_terminal_event_failure_rolls_back_decision_and_review_update(
    session_factory: SessionFactory,
) -> None:
    """A terminal-event collision leaves the second review pending."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
    )

    second_review = create_recommendation_review(
        recommendation_id=SECOND_RECOMMENDATION_ID,
        recommendation=make_recommendation(),
        created_at=CREATED_AT,
    )
    repository.create_review(
        second_review,
        event_id=SECOND_CREATION_EVENT_ID,
    )

    with pytest.raises(IntegrityError):
        repository.reject_review(
            SECOND_RECOMMENDATION_ID,
            decision_id=REJECTION_DECISION_ID,
            event_id=DECISION_EVENT_ID,
            decided_by="planner@example.com",
            decided_at=DECIDED_AT + timedelta(hours=1),
            reason="Supplier delivery is already confirmed",
        )

    assert repository.get_review(SECOND_RECOMMENDATION_ID) == second_review
    assert repository.list_audit_events(SECOND_RECOMMENDATION_ID) == (
        make_creation_event(
            second_review,
            event_id=SECOND_CREATION_EVENT_ID,
        ),
    )

    with session_factory() as session:
        decision_count = session.scalar(
            select(func.count())
            .select_from(RecommendationDecisionRow)
            .where(
                RecommendationDecisionRow.recommendation_id == SECOND_RECOMMENDATION_ID
            )
        )

    assert decision_count == 0


def test_approval_after_rejection_conflicts_without_mutation(
    session_factory: SessionFactory,
) -> None:
    """An approved transition cannot replace a rejected transition."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    rejected = repository.reject_review(
        RECOMMENDATION_ID,
        decision_id=REJECTION_DECISION_ID,
        event_id=REJECTION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        reason="Supplier delivery is already confirmed",
    )
    original_history = repository.list_audit_events(RECOMMENDATION_ID)

    with pytest.raises(RecommendationReviewConflictError):
        repository.approve_review(
            RECOMMENDATION_ID,
            decision_id=DECISION_ID,
            event_id=DECISION_EVENT_ID,
            decided_by="planner@example.com",
            decided_at=DECIDED_AT + timedelta(hours=1),
        )

    assert repository.get_review(RECOMMENDATION_ID) == rejected
    assert repository.list_audit_events(RECOMMENDATION_ID) == original_history


def test_concurrent_approval_and_rejection_have_one_winner(
    session_factory: SessionFactory,
) -> None:
    """A row lock serializes conflicting terminal transitions."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    start_barrier = Barrier(2)
    outcomes: Queue[tuple[str, object]] = Queue()

    def approve_worker() -> None:
        worker_repository = make_repository(session_factory)
        try:
            start_barrier.wait()
            review = worker_repository.approve_review(
                RECOMMENDATION_ID,
                decision_id=DECISION_ID,
                event_id=DECISION_EVENT_ID,
                decided_by="approver@example.com",
                decided_at=DECIDED_AT,
            )
        except RecommendationReviewConflictError as error:
            outcomes.put(("conflict", error))
        except Exception as error:
            outcomes.put(("error", error))
        else:
            outcomes.put(("approved", review))

    def reject_worker() -> None:
        worker_repository = make_repository(session_factory)
        try:
            start_barrier.wait()
            review = worker_repository.reject_review(
                RECOMMENDATION_ID,
                decision_id=REJECTION_DECISION_ID,
                event_id=REJECTION_EVENT_ID,
                decided_by="rejector@example.com",
                decided_at=DECIDED_AT,
                reason="Do not replenish",
            )
        except RecommendationReviewConflictError as error:
            outcomes.put(("conflict", error))
        except Exception as error:
            outcomes.put(("error", error))
        else:
            outcomes.put(("rejected", review))

    threads = (
        Thread(target=approve_worker),
        Thread(target=reject_worker),
    )
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert all(not thread.is_alive() for thread in threads)

    received = (
        outcomes.get(timeout=2),
        outcomes.get(timeout=2),
    )
    labels = tuple(label for label, _ in received)

    assert "error" not in labels
    assert labels.count("conflict") == 1
    assert sum(label in {"approved", "rejected"} for label in labels) == 1

    conflict = next(value for label, value in received if label == "conflict")
    winner = next(
        value for label, value in received if label in {"approved", "rejected"}
    )

    assert isinstance(
        conflict,
        RecommendationReviewConflictError,
    )
    assert isinstance(winner, ReorderRecommendationReview)

    stored = repository.get_review(RECOMMENDATION_ID)
    events = repository.list_audit_events(RECOMMENDATION_ID)

    assert stored == winner
    assert stored.decision is not None
    assert len(events) == 2
    assert tuple(event.sequence_number for event in events) == (
        1,
        2,
    )
    assert events[-1].review_status is stored.review_status
    assert events[-1].decision_id == stored.decision.decision_id

    with session_factory() as session:
        decision_count = session.scalar(
            select(func.count())
            .select_from(RecommendationDecisionRow)
            .where(RecommendationDecisionRow.recommendation_id == RECOMMENDATION_ID)
        )
        event_count = session.scalar(
            select(func.count())
            .select_from(RecommendationAuditEventRow)
            .where(RecommendationAuditEventRow.recommendation_id == RECOMMENDATION_ID)
        )

    assert decision_count == 1
    assert event_count == 2


def test_noncontiguous_persisted_audit_history_is_detected(
    session_factory: SessionFactory,
) -> None:
    """A terminal event without its creation event is rejected on read."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
    )

    with session_factory() as session:
        creation_row = session.get(
            RecommendationAuditEventRow,
            CREATION_EVENT_ID,
        )
        assert creation_row is not None
        session.delete(creation_row)
        session.commit()

    with pytest.raises(
        RuntimeError,
        match="audit sequence is not contiguous",
    ):
        repository.list_audit_events(RECOMMENDATION_ID)


def test_terminal_review_with_incomplete_history_is_detected(
    session_factory: SessionFactory,
) -> None:
    """A terminal review must retain creation and terminal events."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
    )

    with session_factory() as session:
        terminal_row = session.get(
            RecommendationAuditEventRow,
            DECISION_EVENT_ID,
        )
        assert terminal_row is not None
        session.delete(terminal_row)
        session.commit()

    with pytest.raises(
        RuntimeError,
        match="Terminal review audit history is inconsistent",
    ):
        repository.list_audit_events(RECOMMENDATION_ID)


def test_persisted_audit_quantity_must_match_review_snapshot(
    session_factory: SessionFactory,
) -> None:
    """Cross-row quantity drift is rejected on repository reads."""
    repository = make_repository(session_factory)
    pending = create_pending_workflow(
        session_factory,
        repository,
    )

    with session_factory() as session:
        creation_row = session.get(
            RecommendationAuditEventRow,
            CREATION_EVENT_ID,
        )
        assert creation_row is not None
        creation_row.recommended_reorder_quantity = (
            pending.recommendation.recommended_reorder_quantity + 1
        )
        session.commit()

    with pytest.raises(
        RuntimeError,
        match="audit history does not match its review",
    ):
        repository.list_audit_events(RECOMMENDATION_ID)


def test_pending_review_with_terminal_audit_event_is_detected(
    session_factory: SessionFactory,
) -> None:
    """A pending review cannot expose a terminal audit event."""
    repository = make_repository(session_factory)
    pending = create_pending_workflow(
        session_factory,
        repository,
    )

    approved = approve_recommendation(
        review=pending,
        decision_id=DECISION_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        approved_quantity=35,
        note="Expedite replenishment",
    )
    decision = approved.decision
    assert decision is not None

    decision_event = create_review_decision_audit_event(
        event_id=DECISION_EVENT_ID,
        review=approved,
        sequence_number=2,
    )

    with session_factory() as session:
        session.add(
            recommendation_decision_to_row(
                RECOMMENDATION_ID,
                decision,
            )
        )
        session.flush()
        session.add(recommendation_audit_event_to_row(decision_event))
        session.commit()

    with pytest.raises(
        RuntimeError,
        match="Pending review audit history is inconsistent",
    ):
        repository.list_audit_events(RECOMMENDATION_ID)


def test_terminal_audit_timestamp_must_match_decision(
    session_factory: SessionFactory,
) -> None:
    """Audit event time cannot silently diverge from its decision."""
    repository = make_repository(session_factory)
    create_pending_workflow(session_factory, repository)

    repository.approve_review(
        RECOMMENDATION_ID,
        decision_id=DECISION_ID,
        event_id=DECISION_EVENT_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
    )

    with session_factory() as session:
        terminal_row = session.get(
            RecommendationAuditEventRow,
            DECISION_EVENT_ID,
        )
        assert terminal_row is not None
        terminal_row.occurred_at = DECIDED_AT + timedelta(minutes=1)
        session.commit()

    with pytest.raises(
        RuntimeError,
        match="Terminal review and audit event do not match",
    ):
        repository.list_audit_events(RECOMMENDATION_ID)
