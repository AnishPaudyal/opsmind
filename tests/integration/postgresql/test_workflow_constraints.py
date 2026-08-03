"""Real-PostgreSQL recommendation-workflow row and constraint tests."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.recommendation_audit import (
    RecommendationAuditEvent,
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
from opsmind.persistence.postgresql.database import SessionFactory
from opsmind.persistence.postgresql.mappings import (
    recommendation_audit_event_row_to_domain,
    recommendation_audit_event_to_row,
    recommendation_decision_to_row,
    recommendation_review_rows_to_domain,
    recommendation_review_to_row,
)
from opsmind.persistence.postgresql.models import (
    ProductRow,
    RecommendationAuditEventRow,
    RecommendationDecisionRow,
    RecommendationReviewRow,
)

PRODUCT_ID = UUID("50000000-0000-0000-0000-000000000001")

RECOMMENDATION_ID = UUID("60000000-0000-0000-0000-000000000001")
OTHER_RECOMMENDATION_ID = UUID("60000000-0000-0000-0000-000000000002")

APPROVAL_ID = UUID("70000000-0000-0000-0000-000000000001")
REJECTION_ID = UUID("70000000-0000-0000-0000-000000000002")
OTHER_DECISION_ID = UUID("70000000-0000-0000-0000-000000000003")

CREATION_EVENT_ID = UUID("80000000-0000-0000-0000-000000000001")
APPROVAL_EVENT_ID = UUID("80000000-0000-0000-0000-000000000002")
REJECTION_EVENT_ID = UUID("80000000-0000-0000-0000-000000000003")

CREATED_AT = datetime(2026, 8, 3, 15, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 8, 3, 16, 0, tzinfo=UTC)


def make_recommendation() -> ReorderRecommendation:
    """Build one actionable recommendation snapshot."""
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


def make_pending_review(
    recommendation_id: UUID = RECOMMENDATION_ID,
) -> ReorderRecommendationReview:
    """Build one valid pending recommendation review."""
    return create_recommendation_review(
        recommendation_id=recommendation_id,
        recommendation=make_recommendation(),
        created_at=CREATED_AT,
    )


def make_approved_review(
    pending_review: ReorderRecommendationReview,
    decision_id: UUID = APPROVAL_ID,
) -> ReorderRecommendationReview:
    """Build one valid approved recommendation review."""
    return approve_recommendation(
        review=pending_review,
        decision_id=decision_id,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        approved_quantity=36,
        note="Expedite replenishment",
    )


def make_rejected_review(
    pending_review: ReorderRecommendationReview,
) -> ReorderRecommendationReview:
    """Build one valid rejected recommendation review."""
    return reject_recommendation(
        review=pending_review,
        decision_id=REJECTION_ID,
        decided_by="planner@example.com",
        decided_at=DECIDED_AT,
        reason="Supplier delivery is already confirmed",
    )


def _constraint_name(error: IntegrityError) -> str | None:
    """Return a Psycopg-reported constraint name without exposing SQL."""
    diagnostic = getattr(error.orig, "diag", None)
    name = getattr(diagnostic, "constraint_name", None)
    return name if isinstance(name, str) else None


def _persist_product(session: Session) -> None:
    """Insert the product required by workflow review foreign keys."""
    session.add(
        ProductRow(
            id=PRODUCT_ID,
            sku="WORKFLOW-TEST-001",
            name="Workflow Constraint Test Product",
            unit_of_measure="units",
            lead_time_days=7,
            is_active=True,
        )
    )
    session.flush()


def _persist_pending_review(
    session: Session,
    recommendation_id: UUID = RECOMMENDATION_ID,
) -> tuple[ReorderRecommendationReview, RecommendationReviewRow]:
    """Insert and return one pending review and its row."""
    review = make_pending_review(recommendation_id)
    row = recommendation_review_to_row(review)
    session.add(row)
    session.flush()
    return review, row


def _persist_terminal_workflow(
    session: Session,
    pending_review: ReorderRecommendationReview,
    terminal_review: ReorderRecommendationReview,
    terminal_event_id: UUID,
) -> tuple[RecommendationAuditEvent, RecommendationAuditEvent]:
    """Persist one complete valid workflow in dependency-safe order."""
    decision = terminal_review.decision
    assert decision is not None

    review_row = recommendation_review_to_row(pending_review)
    creation_event = create_review_created_audit_event(
        event_id=CREATION_EVENT_ID,
        review=pending_review,
        sequence_number=1,
    )
    decision_event = create_review_decision_audit_event(
        event_id=terminal_event_id,
        review=terminal_review,
        sequence_number=2,
    )

    session.add(review_row)
    session.flush()

    session.add(recommendation_audit_event_to_row(creation_event))
    session.add(
        recommendation_decision_to_row(
            terminal_review.recommendation_id,
            decision,
        )
    )
    session.flush()

    review_row.review_status = terminal_review.review_status.value
    review_row.decision_id = decision.decision_id

    session.add(recommendation_audit_event_to_row(decision_event))
    session.commit()

    return creation_event, decision_event


def _load_audit_events(
    session: Session,
    recommendation_id: UUID,
) -> tuple[RecommendationAuditEvent, ...]:
    """Load one workflow's audit events in authoritative sequence order."""
    rows = session.scalars(
        select(RecommendationAuditEventRow)
        .where(RecommendationAuditEventRow.recommendation_id == recommendation_id)
        .order_by(RecommendationAuditEventRow.sequence_number)
    ).all()

    return tuple(recommendation_audit_event_row_to_domain(row) for row in rows)


def test_pending_review_and_creation_event_persist(
    session_factory: SessionFactory,
) -> None:
    """PostgreSQL accepts a valid pending review and creation event."""
    review = make_pending_review()
    event = create_review_created_audit_event(
        event_id=CREATION_EVENT_ID,
        review=review,
        sequence_number=1,
    )

    with session_factory() as session:
        _persist_product(session)

        session.add(recommendation_review_to_row(review))
        session.flush()

        session.add(recommendation_audit_event_to_row(event))
        session.commit()

    with session_factory() as session:
        stored_review = session.get(
            RecommendationReviewRow,
            RECOMMENDATION_ID,
        )
        stored_event = session.get(
            RecommendationAuditEventRow,
            CREATION_EVENT_ID,
        )

        assert stored_review is not None
        assert stored_event is not None
        assert (
            recommendation_review_rows_to_domain(
                stored_review,
                None,
            )
            == review
        )
        assert recommendation_audit_event_row_to_domain(stored_event) == event
        assert stored_review.available_inventory == -5


def test_approved_workflow_persists_complete_aggregate(
    session_factory: SessionFactory,
) -> None:
    """PostgreSQL accepts an approved review and ordered event history."""
    pending_review = make_pending_review()
    approved_review = make_approved_review(pending_review)

    with session_factory() as session:
        _persist_product(session)
        expected_events = _persist_terminal_workflow(
            session,
            pending_review,
            approved_review,
            APPROVAL_EVENT_ID,
        )

    with session_factory() as session:
        stored_review = session.get(
            RecommendationReviewRow,
            RECOMMENDATION_ID,
        )
        stored_decision = session.get(
            RecommendationDecisionRow,
            APPROVAL_ID,
        )

        assert stored_review is not None
        assert stored_decision is not None
        assert (
            recommendation_review_rows_to_domain(
                stored_review,
                stored_decision,
            )
            == approved_review
        )
        assert _load_audit_events(session, RECOMMENDATION_ID) == expected_events


def test_rejected_workflow_persists_complete_aggregate(
    session_factory: SessionFactory,
) -> None:
    """PostgreSQL accepts a rejected review and its required reason."""
    pending_review = make_pending_review()
    rejected_review = make_rejected_review(pending_review)

    with session_factory() as session:
        _persist_product(session)
        expected_events = _persist_terminal_workflow(
            session,
            pending_review,
            rejected_review,
            REJECTION_EVENT_ID,
        )

    with session_factory() as session:
        stored_review = session.get(
            RecommendationReviewRow,
            RECOMMENDATION_ID,
        )
        stored_decision = session.get(
            RecommendationDecisionRow,
            REJECTION_ID,
        )

        assert stored_review is not None
        assert stored_decision is not None
        assert (
            recommendation_review_rows_to_domain(
                stored_review,
                stored_decision,
            )
            == rejected_review
        )
        assert _load_audit_events(session, RECOMMENDATION_ID) == expected_events


def test_review_rejects_inconsistent_available_inventory(
    session_factory: SessionFactory,
) -> None:
    """Stored available inventory must match on-hand minus allocated."""
    with session_factory() as session:
        _persist_product(session)

        row = recommendation_review_to_row(make_pending_review())
        row.available_inventory = 100
        session.add(row)

        with pytest.raises(IntegrityError) as error:
            session.flush()

        assert _constraint_name(error.value) == (
            "ck_recommendation_reviews_available_inventory_consistent"
        )
        session.rollback()


def test_terminal_review_requires_decision_pointer(
    session_factory: SessionFactory,
) -> None:
    """A terminal review cannot be stored with a null decision pointer."""
    with session_factory() as session:
        _persist_product(session)

        row = recommendation_review_to_row(make_pending_review())
        row.review_status = "approved"
        session.add(row)

        with pytest.raises(IntegrityError) as error:
            session.flush()

        assert _constraint_name(error.value) == (
            "ck_recommendation_reviews_review_decision_shape"
        )
        session.rollback()


def test_approved_decision_requires_positive_quantity(
    session_factory: SessionFactory,
) -> None:
    """An approved decision cannot omit its approved quantity."""
    with session_factory() as session:
        _persist_product(session)
        pending_review, _ = _persist_pending_review(session)

        approved_review = make_approved_review(pending_review)
        decision = approved_review.decision
        assert decision is not None

        row = recommendation_decision_to_row(
            approved_review.recommendation_id,
            decision,
        )
        row.approved_quantity = None
        session.add(row)

        with pytest.raises(IntegrityError) as error:
            session.flush()

        assert _constraint_name(error.value) == (
            "ck_recommendation_decisions_decision_shape"
        )
        session.rollback()


def test_creation_event_requires_sequence_one(
    session_factory: SessionFactory,
) -> None:
    """A creation event cannot be stored as sequence two."""
    with session_factory() as session:
        _persist_product(session)
        pending_review, _ = _persist_pending_review(session)

        event = create_review_created_audit_event(
            event_id=CREATION_EVENT_ID,
            review=pending_review,
            sequence_number=1,
        )
        row = recommendation_audit_event_to_row(event)
        row.sequence_number = 2
        session.add(row)

        with pytest.raises(IntegrityError) as error:
            session.flush()

        assert _constraint_name(error.value) == (
            "ck_recommendation_audit_events_event_shape"
        )
        session.rollback()


def test_review_decision_pointer_requires_matching_pair(
    session_factory: SessionFactory,
) -> None:
    """A review cannot point at another review's decision."""
    with session_factory() as session:
        _persist_product(session)

        first_review, _ = _persist_pending_review(
            session,
            RECOMMENDATION_ID,
        )
        _, second_row = _persist_pending_review(
            session,
            OTHER_RECOMMENDATION_ID,
        )

        approved_first = make_approved_review(first_review)
        decision = approved_first.decision
        assert decision is not None

        session.add(
            recommendation_decision_to_row(
                RECOMMENDATION_ID,
                decision,
            )
        )
        session.flush()

        second_row.review_status = "approved"
        second_row.decision_id = APPROVAL_ID

        with pytest.raises(IntegrityError) as error:
            session.flush()

        assert _constraint_name(error.value) == (
            "fk_recommendation_reviews_decision_pair"
        )
        session.rollback()


def test_review_allows_only_one_decision(
    session_factory: SessionFactory,
) -> None:
    """A recommendation review cannot acquire two decision rows."""
    with session_factory() as session:
        _persist_product(session)
        pending_review, _ = _persist_pending_review(session)

        first_approval = make_approved_review(
            pending_review,
            APPROVAL_ID,
        )
        second_approval = make_approved_review(
            pending_review,
            OTHER_DECISION_ID,
        )

        first_decision = first_approval.decision
        second_decision = second_approval.decision
        assert first_decision is not None
        assert second_decision is not None

        session.add(
            recommendation_decision_to_row(
                RECOMMENDATION_ID,
                first_decision,
            )
        )
        session.flush()

        session.add(
            recommendation_decision_to_row(
                RECOMMENDATION_ID,
                second_decision,
            )
        )

        with pytest.raises(IntegrityError) as error:
            session.flush()

        assert _constraint_name(error.value) == (
            "uq_recommendation_decisions_recommendation_id"
        )
        session.rollback()
