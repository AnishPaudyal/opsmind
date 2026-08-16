"""Repository interface for stored recommendation review workflows."""

from datetime import datetime
from typing import Protocol
from uuid import UUID

from opsmind.domain.recommendation_audit import RecommendationAuditEvent
from opsmind.domain.recommendation_review import (
    RecommendationReviewStatus,
    ReorderRecommendationReview,
)


class RecommendationWorkflowRepository(Protocol):
    """Persist and atomically transition recommendation reviews."""

    def create_review(
        self,
        review: ReorderRecommendationReview,
        *,
        event_id: UUID,
    ) -> ReorderRecommendationReview:
        """Atomically store a new review and its creation event."""
        ...

    def get_review(self, recommendation_id: UUID) -> ReorderRecommendationReview:
        """Return a stored review or raise a typed not-found error."""
        ...

    def list_reviews(
        self,
        *,
        product_id: UUID | None = None,
        review_status: RecommendationReviewStatus | None = None,
    ) -> tuple[ReorderRecommendationReview, ...]:
        """Return matching reviews newest first with a stable identifier tie-break."""
        ...

    def list_audit_events(
        self,
        recommendation_id: UUID,
    ) -> tuple[RecommendationAuditEvent, ...]:
        """Return one review's immutable audit history in sequence order."""
        ...

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
        """Atomically approve or retry an approval."""
        ...

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
        """Atomically reject or retry a rejection."""
        ...
