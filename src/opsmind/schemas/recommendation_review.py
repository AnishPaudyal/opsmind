"""Public schemas for stored recommendation-review workflows."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from opsmind.domain.recommendation_review import (
    RecommendationDecisionType,
    RecommendationReviewStatus,
)
from opsmind.schemas.reorder import ReorderRecommendationResponse


def _strip_required(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("must not be empty")
    return normalized


class ApproveRecommendationRequest(BaseModel):
    """Caller-supplied approval details without authoritative actor identity."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "approved_quantity": 19,
                "note": "Approved as recommended.",
            }
        },
    )
    approved_quantity: int | None = Field(
        default=None,
        ge=1,
        strict=True,
        description="Approved whole-unit quantity; defaults to the recommendation.",
    )
    note: str | None = Field(
        default=None,
        description="Optional decision note; blank input is stored as null.",
    )

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        """Trim an optional note and normalize blank text to null."""
        if value is None:
            return None
        return value.strip() or None


class RejectRecommendationRequest(BaseModel):
    """Caller-supplied rejection details without authoritative actor identity."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "example": {
                "reason": "Inbound inventory is already scheduled.",
            }
        },
    )
    reason: str = Field(description="Required explanation for rejection.")

    @field_validator("reason")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        """Trim required text and reject blank values."""
        return _strip_required(value)


class RecommendationDecisionResponse(BaseModel):
    """Public representation of one terminal decision."""

    decision_id: UUID = Field(description="Server-generated decision identifier.")
    decision_type: RecommendationDecisionType = Field(
        description="Terminal approval or rejection type."
    )
    decided_by: str = Field(description="Stable trusted-principal identifier.")
    decided_at: datetime = Field(description="Timezone-aware UTC decision time.")
    approved_quantity: int | None = Field(
        description="Approved quantity, or null for a rejection."
    )
    note: str | None = Field(
        description="Optional approval note or required rejection reason."
    )


class ReorderRecommendationReviewResponse(BaseModel):
    """Stored immutable recommendation snapshot and review state."""

    recommendation_id: UUID = Field(
        description="Stable server-generated workflow identifier."
    )
    recommendation: ReorderRecommendationResponse = Field(
        description="Immutable recommendation and its original evidence."
    )
    review_status: RecommendationReviewStatus = Field(
        description="Current pending or terminal review state."
    )
    created_at: datetime = Field(description="Timezone-aware UTC creation time.")
    decision: RecommendationDecisionResponse | None = Field(
        description="Terminal decision, or null while review is pending."
    )
