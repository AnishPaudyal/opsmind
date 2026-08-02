"""Public schemas for recommendation workflow audit history."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from opsmind.domain.recommendation_audit import RecommendationAuditEventType
from opsmind.domain.recommendation_review import RecommendationReviewStatus


class RecommendationAuditEventResponse(BaseModel):
    """One immutable event in a recommendation review history."""

    event_id: UUID = Field(description="Server-generated audit event identifier.")
    recommendation_id: UUID = Field(description="Stored recommendation identifier.")
    sequence_number: int = Field(
        ge=1,
        description="Per-recommendation ordering number starting at one.",
    )
    event_type: RecommendationAuditEventType = Field(
        description="Workflow event represented by this record."
    )
    occurred_at: datetime = Field(description="Timezone-aware UTC event time.")
    review_status: RecommendationReviewStatus = Field(
        description="Review status produced by the event."
    )
    decision_id: UUID | None = Field(
        description="Linked terminal decision identifier, when applicable."
    )
    actor: str | None = Field(
        description="Unverified caller-supplied actor for a terminal decision."
    )
    recommended_reorder_quantity: int = Field(
        ge=1,
        description="Original system-recommended whole-unit quantity.",
    )
    approved_quantity: int | None = Field(
        ge=1,
        description="Approved whole-unit quantity, or null otherwise.",
    )
    note: str | None = Field(
        description="Optional approval note or required rejection reason."
    )


class RecommendationAuditHistoryResponse(BaseModel):
    """Sequence-ordered immutable audit history for one recommendation."""

    recommendation_id: UUID = Field(description="Stored recommendation identifier.")
    events: list[RecommendationAuditEventResponse] = Field(
        description="Events ordered by ascending per-recommendation sequence."
    )
