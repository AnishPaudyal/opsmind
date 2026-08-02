"""Pure recommendation-review state and transition rules."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from opsmind.domain.errors import (
    NoActionableReorderRecommendationError,
    RecommendationReviewConflictError,
)
from opsmind.domain.reorder import (
    ReorderRecommendation,
    ReorderRecommendationStatus,
)


class RecommendationReviewStatus(StrEnum):
    """Supported states for a stored recommendation review."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RecommendationDecisionType(StrEnum):
    """Supported terminal recommendation decisions."""

    APPROVED = "approved"
    REJECTED = "rejected"


def _normalize_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_positive_quantity(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


def _validate_actionable(recommendation: ReorderRecommendation) -> None:
    if recommendation.recommendation_status is not (
        ReorderRecommendationStatus.REORDER_RECOMMENDED
    ):
        raise NoActionableReorderRecommendationError(recommendation.product_id)
    try:
        _validate_positive_quantity(
            recommendation.recommended_reorder_quantity,
            "recommended_reorder_quantity",
        )
    except ValueError:
        raise NoActionableReorderRecommendationError(
            recommendation.product_id
        ) from None


@dataclass(frozen=True, slots=True)
class RecommendationDecision:
    """One immutable terminal human decision."""

    decision_id: UUID
    decision_type: RecommendationDecisionType
    decided_by: str
    decided_at: datetime
    approved_quantity: int | None
    note: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.decision_type, RecommendationDecisionType):
            raise ValueError("decision_type must be a supported decision type")
        object.__setattr__(
            self,
            "decided_by",
            _normalize_required_text(self.decided_by, "decided_by"),
        )
        object.__setattr__(
            self,
            "decided_at",
            _normalize_utc(self.decided_at, "decided_at"),
        )
        object.__setattr__(self, "note", _normalize_optional_text(self.note))

        if self.decision_type is RecommendationDecisionType.APPROVED:
            if self.approved_quantity is None:
                raise ValueError("approved decisions require approved_quantity")
            _validate_positive_quantity(
                self.approved_quantity,
                "approved_quantity",
            )
            return

        if self.approved_quantity is not None:
            raise ValueError("rejected decisions must not have approved_quantity")
        if self.note is None:
            raise ValueError("rejected decisions require a non-empty note")


@dataclass(frozen=True, slots=True)
class ReorderRecommendationReview:
    """Immutable recommendation snapshot and its current review state."""

    recommendation_id: UUID
    recommendation: ReorderRecommendation
    review_status: RecommendationReviewStatus
    created_at: datetime
    decision: RecommendationDecision | None

    def __post_init__(self) -> None:
        if not isinstance(self.review_status, RecommendationReviewStatus):
            raise ValueError("review_status must be a supported review status")
        _validate_actionable(self.recommendation)
        object.__setattr__(
            self,
            "created_at",
            _normalize_utc(self.created_at, "created_at"),
        )

        if self.review_status is RecommendationReviewStatus.PENDING_REVIEW:
            if self.decision is not None:
                raise ValueError("pending reviews must not have a decision")
            return

        if self.decision is None:
            raise ValueError("terminal reviews require a decision")
        if self.review_status.value != self.decision.decision_type.value:
            raise ValueError("review status must match decision type")


def create_recommendation_review(
    *,
    recommendation_id: UUID,
    recommendation: ReorderRecommendation,
    created_at: datetime,
) -> ReorderRecommendationReview:
    """Create a pending review for one actionable recommendation snapshot."""
    _validate_actionable(recommendation)
    return ReorderRecommendationReview(
        recommendation_id=recommendation_id,
        recommendation=recommendation,
        review_status=RecommendationReviewStatus.PENDING_REVIEW,
        created_at=created_at,
        decision=None,
    )


def approve_recommendation(
    *,
    review: ReorderRecommendationReview,
    decision_id: UUID,
    decided_by: str,
    decided_at: datetime,
    approved_quantity: int | None = None,
    note: str | None = None,
) -> ReorderRecommendationReview:
    """Approve a pending review or return an identical prior approval."""
    normalized_actor = _normalize_required_text(decided_by, "decided_by")
    normalized_note = _normalize_optional_text(note)
    normalized_time = _normalize_utc(decided_at, "decided_at")
    resolved_quantity = (
        review.recommendation.recommended_reorder_quantity
        if approved_quantity is None
        else approved_quantity
    )
    _validate_positive_quantity(resolved_quantity, "approved_quantity")

    if review.review_status is RecommendationReviewStatus.APPROVED:
        decision = review.decision
        if (
            decision is not None
            and decision.decided_by == normalized_actor
            and decision.approved_quantity == resolved_quantity
            and decision.note == normalized_note
        ):
            return review
        raise RecommendationReviewConflictError(
            "Recommendation is already approved with a different decision."
        )
    if review.review_status is RecommendationReviewStatus.REJECTED:
        raise RecommendationReviewConflictError(
            "A rejected recommendation cannot be approved."
        )

    decision = RecommendationDecision(
        decision_id=decision_id,
        decision_type=RecommendationDecisionType.APPROVED,
        decided_by=normalized_actor,
        decided_at=normalized_time,
        approved_quantity=resolved_quantity,
        note=normalized_note,
    )
    return ReorderRecommendationReview(
        recommendation_id=review.recommendation_id,
        recommendation=review.recommendation,
        review_status=RecommendationReviewStatus.APPROVED,
        created_at=review.created_at,
        decision=decision,
    )


def reject_recommendation(
    *,
    review: ReorderRecommendationReview,
    decision_id: UUID,
    decided_by: str,
    decided_at: datetime,
    reason: str,
) -> ReorderRecommendationReview:
    """Reject a pending review or return an identical prior rejection."""
    normalized_actor = _normalize_required_text(decided_by, "decided_by")
    normalized_reason = _normalize_required_text(reason, "reason")
    normalized_time = _normalize_utc(decided_at, "decided_at")

    if review.review_status is RecommendationReviewStatus.REJECTED:
        decision = review.decision
        if (
            decision is not None
            and decision.decided_by == normalized_actor
            and decision.note == normalized_reason
        ):
            return review
        raise RecommendationReviewConflictError(
            "Recommendation is already rejected with a different decision."
        )
    if review.review_status is RecommendationReviewStatus.APPROVED:
        raise RecommendationReviewConflictError(
            "An approved recommendation cannot be rejected."
        )

    decision = RecommendationDecision(
        decision_id=decision_id,
        decision_type=RecommendationDecisionType.REJECTED,
        decided_by=normalized_actor,
        decided_at=normalized_time,
        approved_quantity=None,
        note=normalized_reason,
    )
    return ReorderRecommendationReview(
        recommendation_id=review.recommendation_id,
        recommendation=review.recommendation,
        review_status=RecommendationReviewStatus.REJECTED,
        created_at=review.created_at,
        decision=decision,
    )
