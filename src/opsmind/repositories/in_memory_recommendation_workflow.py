"""Thread-safe process-local recommendation workflow repository."""

from datetime import datetime
from threading import RLock
from uuid import UUID

from opsmind.domain.errors import (
    DuplicateRecommendationReviewError,
    RecommendationReviewNotFoundError,
)
from opsmind.domain.recommendation_review import (
    ReorderRecommendationReview,
    approve_recommendation,
    reject_recommendation,
)


class InMemoryRecommendationWorkflowRepository:
    """Store immutable recommendation reviews for one application instance."""

    def __init__(self) -> None:
        self._reviews: dict[UUID, ReorderRecommendationReview] = {}
        self._lock = RLock()

    def create_review(
        self,
        review: ReorderRecommendationReview,
    ) -> ReorderRecommendationReview:
        """Atomically store a new review without overwriting an identifier."""
        with self._lock:
            if review.recommendation_id in self._reviews:
                raise DuplicateRecommendationReviewError(review.recommendation_id)
            self._reviews[review.recommendation_id] = review
            return review

    def get_review(self, recommendation_id: UUID) -> ReorderRecommendationReview:
        """Return one immutable stored review."""
        with self._lock:
            try:
                return self._reviews[recommendation_id]
            except KeyError:
                raise RecommendationReviewNotFoundError(recommendation_id) from None

    def approve_review(
        self,
        recommendation_id: UUID,
        *,
        decision_id: UUID,
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
            self._reviews[recommendation_id] = updated
            return updated

    def reject_review(
        self,
        recommendation_id: UUID,
        *,
        decision_id: UUID,
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
            self._reviews[recommendation_id] = updated
            return updated
