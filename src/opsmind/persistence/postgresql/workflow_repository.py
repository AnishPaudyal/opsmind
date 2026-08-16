"""Synchronous PostgreSQL recommendation workflow repository."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from opsmind.domain.errors import (
    DuplicateRecommendationReviewError,
    RecommendationReviewNotFoundError,
)
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
    reject_recommendation,
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
    RecommendationAuditEventRow,
    RecommendationDecisionRow,
    RecommendationReviewRow,
)

LockMode = Literal["share", "update"]

RECOMMENDATION_REVIEW_PRIMARY_KEY_CONSTRAINT = "pk_recommendation_reviews"


def _constraint_name(error: IntegrityError) -> str | None:
    """Return a Psycopg-reported constraint name without exposing SQL."""
    diagnostic = getattr(error.orig, "diag", None)
    name = getattr(diagnostic, "constraint_name", None)
    return name if isinstance(name, str) else None


class PostgresRecommendationWorkflowRepository:
    """Persist recommendation workflow state through short-lived sessions."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def create_review(
        self,
        review: ReorderRecommendationReview,
        *,
        event_id: UUID,
    ) -> ReorderRecommendationReview:
        """Atomically persist a pending review and its creation event."""
        creation_event = create_review_created_audit_event(
            event_id=event_id,
            review=review,
            sequence_number=1,
        )
        review_row = recommendation_review_to_row(review)
        event_row = recommendation_audit_event_to_row(creation_event)

        with self._session_factory() as session:
            try:
                session.add(review_row)
                session.flush()

                session.add(event_row)
                session.flush()

                session.commit()
            except IntegrityError as error:
                session.rollback()
                if _constraint_name(error) == (
                    RECOMMENDATION_REVIEW_PRIMARY_KEY_CONSTRAINT
                ):
                    raise DuplicateRecommendationReviewError(
                        review.recommendation_id
                    ) from None
                raise
            except SQLAlchemyError:
                session.rollback()
                raise

        return review

    def get_review(
        self,
        recommendation_id: UUID,
    ) -> ReorderRecommendationReview:
        """Return one detached immutable review aggregate."""
        with self._session_factory() as session:
            review_row, decision_row = self._load_review_rows(
                session,
                recommendation_id,
            )
            return self._review_from_rows(review_row, decision_row)

    def list_reviews(
        self,
        *,
        product_id: UUID | None = None,
        review_status: RecommendationReviewStatus | None = None,
    ) -> tuple[ReorderRecommendationReview, ...]:
        """Return filtered detached aggregates in deterministic newest-first order."""
        statement = (
            select(RecommendationReviewRow, RecommendationDecisionRow)
            .outerjoin(
                RecommendationDecisionRow,
                and_(
                    RecommendationDecisionRow.recommendation_id
                    == RecommendationReviewRow.recommendation_id,
                    RecommendationDecisionRow.decision_id
                    == RecommendationReviewRow.decision_id,
                ),
            )
            .order_by(
                RecommendationReviewRow.created_at.desc(),
                RecommendationReviewRow.recommendation_id.desc(),
            )
        )
        if product_id is not None:
            statement = statement.where(
                RecommendationReviewRow.product_id == product_id
            )
        if review_status is not None:
            statement = statement.where(
                RecommendationReviewRow.review_status == review_status.value
            )

        with self._session_factory() as session:
            rows = session.execute(statement).all()
            return tuple(
                self._review_from_rows(review_row, decision_row)
                for review_row, decision_row in rows
            )

    def list_audit_events(
        self,
        recommendation_id: UUID,
    ) -> tuple[RecommendationAuditEvent, ...]:
        """Return one validated audit history in sequence order."""
        with self._session_factory() as session:
            review_row, decision_row = self._load_review_rows(
                session,
                recommendation_id,
                lock_mode="share",
            )
            review = self._review_from_rows(
                review_row,
                decision_row,
            )
            events = self._load_audit_events(
                session,
                recommendation_id,
            )
            self._validate_history(review, events)
            return events

    def approve_review(
        self,
        recommendation_id: UUID,
        *,
        decision_id: UUID,
        event_id: UUID,
        decided_by: str,
        decided_at: datetime,
        approved_quantity: int | None = None,
        note: str | None = None,
    ) -> ReorderRecommendationReview:
        """Atomically approve or retry one recommendation review."""
        with self._session_factory() as session:
            review_row, decision_row = self._load_review_rows(
                session,
                recommendation_id,
                lock_mode="update",
            )
            current = self._review_from_rows(
                review_row,
                decision_row,
            )
            events = self._load_audit_events(
                session,
                recommendation_id,
            )
            self._validate_history(current, events)

            updated = approve_recommendation(
                review=current,
                decision_id=decision_id,
                decided_by=decided_by,
                decided_at=decided_at,
                approved_quantity=approved_quantity,
                note=note,
            )
            if updated is current:
                return current

            return self._persist_terminal_review(
                session,
                review_row,
                updated,
                event_id=event_id,
                sequence_number=len(events) + 1,
            )

    def reject_review(
        self,
        recommendation_id: UUID,
        *,
        decision_id: UUID,
        event_id: UUID,
        decided_by: str,
        decided_at: datetime,
        reason: str,
    ) -> ReorderRecommendationReview:
        """Atomically reject or retry one recommendation review."""
        with self._session_factory() as session:
            review_row, decision_row = self._load_review_rows(
                session,
                recommendation_id,
                lock_mode="update",
            )
            current = self._review_from_rows(
                review_row,
                decision_row,
            )
            events = self._load_audit_events(
                session,
                recommendation_id,
            )
            self._validate_history(current, events)

            updated = reject_recommendation(
                review=current,
                decision_id=decision_id,
                decided_by=decided_by,
                decided_at=decided_at,
                reason=reason,
            )
            if updated is current:
                return current

            return self._persist_terminal_review(
                session,
                review_row,
                updated,
                event_id=event_id,
                sequence_number=len(events) + 1,
            )

    @staticmethod
    def _load_review_rows(
        session: Session,
        recommendation_id: UUID,
        *,
        lock_mode: LockMode | None = None,
    ) -> tuple[
        RecommendationReviewRow,
        RecommendationDecisionRow | None,
    ]:
        statement = select(RecommendationReviewRow).where(
            RecommendationReviewRow.recommendation_id == recommendation_id
        )
        if lock_mode == "share":
            statement = statement.with_for_update(read=True)
        elif lock_mode == "update":
            statement = statement.with_for_update()

        review_row = session.scalar(statement)
        if review_row is None:
            raise RecommendationReviewNotFoundError(recommendation_id)

        decision_row: RecommendationDecisionRow | None = None
        if review_row.decision_id is not None:
            decision_row = session.scalar(
                select(RecommendationDecisionRow).where(
                    RecommendationDecisionRow.recommendation_id == recommendation_id,
                    RecommendationDecisionRow.decision_id == review_row.decision_id,
                )
            )

        return review_row, decision_row

    @staticmethod
    def _review_from_rows(
        review_row: RecommendationReviewRow,
        decision_row: RecommendationDecisionRow | None,
    ) -> ReorderRecommendationReview:
        try:
            return recommendation_review_rows_to_domain(
                review_row,
                decision_row,
            )
        except ValueError as error:
            raise RuntimeError(
                "Stored recommendation review is inconsistent."
            ) from error

    @staticmethod
    def _load_audit_events(
        session: Session,
        recommendation_id: UUID,
    ) -> tuple[RecommendationAuditEvent, ...]:
        rows = session.scalars(
            select(RecommendationAuditEventRow)
            .where(RecommendationAuditEventRow.recommendation_id == recommendation_id)
            .order_by(RecommendationAuditEventRow.sequence_number)
        ).all()

        try:
            return tuple(recommendation_audit_event_row_to_domain(row) for row in rows)
        except ValueError as error:
            raise RuntimeError(
                "Stored recommendation audit history is inconsistent."
            ) from error

    @staticmethod
    def _persist_terminal_review(
        session: Session,
        review_row: RecommendationReviewRow,
        review: ReorderRecommendationReview,
        *,
        event_id: UUID,
        sequence_number: int,
    ) -> ReorderRecommendationReview:
        decision = review.decision
        if decision is None:
            raise RuntimeError("A terminal review must contain a decision.")

        decision_event = create_review_decision_audit_event(
            event_id=event_id,
            review=review,
            sequence_number=sequence_number,
        )
        decision_row = recommendation_decision_to_row(
            review.recommendation_id,
            decision,
        )
        event_row = recommendation_audit_event_to_row(decision_event)

        try:
            session.add(decision_row)
            session.flush()

            review_row.review_status = review.review_status.value
            review_row.decision_id = decision.decision_id

            session.add(event_row)
            session.flush()

            session.commit()
        except SQLAlchemyError:
            session.rollback()
            raise

        return review

    @staticmethod
    def _validate_history(
        review: ReorderRecommendationReview,
        events: tuple[RecommendationAuditEvent, ...],
    ) -> None:
        if not events:
            raise RuntimeError("Stored recommendation audit history must not be empty.")

        expected_sequences = tuple(range(1, len(events) + 1))
        actual_sequences = tuple(event.sequence_number for event in events)
        if actual_sequences != expected_sequences:
            raise RuntimeError("Recommendation audit sequence is not contiguous.")

        if any(
            event.recommendation_id != review.recommendation_id
            or event.recommended_reorder_quantity
            != review.recommendation.recommended_reorder_quantity
            for event in events
        ):
            raise RuntimeError(
                "Recommendation audit history does not match its review."
            )

        latest = events[-1]
        if review.review_status is (RecommendationReviewStatus.PENDING_REVIEW):
            if (
                len(events) != 1
                or latest.event_type is not RecommendationAuditEventType.REVIEW_CREATED
            ):
                raise RuntimeError("Pending review audit history is inconsistent.")
            return

        decision = review.decision
        if len(events) != 2 or decision is None:
            raise RuntimeError("Terminal review audit history is inconsistent.")

        expected_event_type = (
            RecommendationAuditEventType.RECOMMENDATION_APPROVED
            if review.review_status is RecommendationReviewStatus.APPROVED
            else RecommendationAuditEventType.RECOMMENDATION_REJECTED
        )
        if (
            latest.event_type is not expected_event_type
            or latest.review_status is not review.review_status
            or latest.decision_id != decision.decision_id
            or latest.occurred_at != decision.decided_at
        ):
            raise RuntimeError("Terminal review and audit event do not match.")
