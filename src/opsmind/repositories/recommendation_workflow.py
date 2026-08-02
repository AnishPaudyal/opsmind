"""Repository interface for stored recommendation review workflows."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from opsmind.domain.recommendation_review import ReorderRecommendationReview


class RecommendationWorkflowRepository(Protocol):
    """Persist and atomically transition recommendation reviews."""

    def create_review(
        self,
        review: ReorderRecommendationReview,
    ) -> ReorderRecommendationReview:
        """Store a new immutable recommendation review."""
        ...

    def get_review(self, recommendation_id: UUID) -> ReorderRecommendationReview:
        """Return a stored review or raise a typed not-found error."""
        ...

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
        """Atomically approve or retry an approval."""
        ...

    def reject_review(
        self,
        recommendation_id: UUID,
        *,
        decision_id: UUID,
        decided_by: str,
        decided_at: datetime,
        reason: str,
    ) -> ReorderRecommendationReview:
        """Atomically reject or retry a rejection."""
        ...
