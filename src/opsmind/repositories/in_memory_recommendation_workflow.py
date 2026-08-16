"""Thread-safe process-local recommendation workflow repository."""

from datetime import datetime
from threading import RLock
from uuid import UUID

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


class InMemoryRecommendationWorkflowRepository:
    """Store immutable recommendation reviews for one application instance."""

    def __init__(self) -> None:
        self._reviews: dict[UUID, ReorderRecommendationReview] = {}
        self._audit_events: dict[UUID, tuple[RecommendationAuditEvent, ...]] = {}
        self._lock = RLock()

    def create_review(
        self,
        review: ReorderRecommendationReview,
        *,
        event_id: UUID,
    ) -> ReorderRecommendationReview:
        """Atomically store a review and its immutable creation event."""
        with self._lock:
            if review.recommendation_id in self._reviews:
                raise DuplicateRecommendationReviewError(review.recommendation_id)
            creation_event = create_review_created_audit_event(
                event_id=event_id,
                review=review,
                sequence_number=1,
            )
            events = (creation_event,)
            self._validate_history(review, events)
            updated_reviews = self._reviews.copy()
            updated_histories = self._audit_events.copy()
            updated_reviews[review.recommendation_id] = review
            updated_histories[review.recommendation_id] = events
            self._reviews = updated_reviews
            self._audit_events = updated_histories
            return review

    def get_review(self, recommendation_id: UUID) -> ReorderRecommendationReview:
        """Return one immutable stored review."""
        with self._lock:
            try:
                return self._reviews[recommendation_id]
            except KeyError:
                raise RecommendationReviewNotFoundError(recommendation_id) from None

    def list_reviews(
        self,
        *,
        product_id: UUID | None = None,
        review_status: RecommendationReviewStatus | None = None,
    ) -> tuple[ReorderRecommendationReview, ...]:
        """Return filtered reviews in deterministic newest-first order."""
        with self._lock:
            matches = (
                review
                for review in self._reviews.values()
                if (
                    product_id is None or review.recommendation.product_id == product_id
                )
                and (review_status is None or review.review_status is review_status)
            )
            return tuple(
                sorted(
                    matches,
                    key=lambda review: (
                        review.created_at,
                        review.recommendation_id.int,
                    ),
                    reverse=True,
                )
            )

    def list_audit_events(
        self,
        recommendation_id: UUID,
    ) -> tuple[RecommendationAuditEvent, ...]:
        """Return an immutable, sequence-ordered history for one review."""
        with self._lock:
            review = self.get_review(recommendation_id)
            events = self._history_for(recommendation_id)
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
        """Apply the full read-transition-write approval under one lock."""
        with self._lock:
            current = self.get_review(recommendation_id)
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
            existing_events = self._history_for(recommendation_id)
            decision_event = create_review_decision_audit_event(
                event_id=event_id,
                review=updated,
                sequence_number=len(existing_events) + 1,
            )
            updated_events = (*existing_events, decision_event)
            self._validate_history(updated, updated_events)
            updated_reviews = self._reviews.copy()
            updated_histories = self._audit_events.copy()
            updated_reviews[recommendation_id] = updated
            updated_histories[recommendation_id] = updated_events
            self._reviews = updated_reviews
            self._audit_events = updated_histories
            return updated

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
        """Apply the full read-transition-write rejection under one lock."""
        with self._lock:
            current = self.get_review(recommendation_id)
            updated = reject_recommendation(
                review=current,
                decision_id=decision_id,
                decided_by=decided_by,
                decided_at=decided_at,
                reason=reason,
            )
            if updated is current:
                return current
            existing_events = self._history_for(recommendation_id)
            decision_event = create_review_decision_audit_event(
                event_id=event_id,
                review=updated,
                sequence_number=len(existing_events) + 1,
            )
            updated_events = (*existing_events, decision_event)
            self._validate_history(updated, updated_events)
            updated_reviews = self._reviews.copy()
            updated_histories = self._audit_events.copy()
            updated_reviews[recommendation_id] = updated
            updated_histories[recommendation_id] = updated_events
            self._reviews = updated_reviews
            self._audit_events = updated_histories
            return updated

    def _history_for(
        self,
        recommendation_id: UUID,
    ) -> tuple[RecommendationAuditEvent, ...]:
        try:
            return self._audit_events[recommendation_id]
        except KeyError:
            raise RuntimeError(
                "Stored recommendation review is missing its audit history."
            ) from None

    @staticmethod
    def _validate_history(
        review: ReorderRecommendationReview,
        events: tuple[RecommendationAuditEvent, ...],
    ) -> None:
        if not events:
            raise RuntimeError("Stored recommendation audit history must not be empty.")
        expected_sequences = tuple(range(1, len(events) + 1))
        if tuple(event.sequence_number for event in events) != expected_sequences:
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
        if review.review_status is RecommendationReviewStatus.PENDING_REVIEW:
            if len(events) != 1 or latest.event_type is not (
                RecommendationAuditEventType.REVIEW_CREATED
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
