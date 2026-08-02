"""Pure append-only audit events for recommendation review workflows."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from opsmind.domain.recommendation_review import (
    RecommendationDecisionType,
    RecommendationReviewStatus,
    ReorderRecommendationReview,
)


class RecommendationAuditEventType(StrEnum):
    """Supported recommendation workflow audit events."""

    REVIEW_CREATED = "review_created"
    RECOMMENDATION_APPROVED = "recommendation_approved"
    RECOMMENDATION_REJECTED = "recommendation_rejected"


def _normalize_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value.astimezone(UTC)


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _validate_positive_integer(value: int, field_name: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class RecommendationAuditEvent:
    """One immutable fact in a recommendation review's ordered history."""

    event_id: UUID
    recommendation_id: UUID
    sequence_number: int
    event_type: RecommendationAuditEventType
    occurred_at: datetime
    review_status: RecommendationReviewStatus
    decision_id: UUID | None
    actor: str | None
    recommended_reorder_quantity: int
    approved_quantity: int | None
    note: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.event_id, UUID):
            raise ValueError("event_id must be a UUID")
        if not isinstance(self.recommendation_id, UUID):
            raise ValueError("recommendation_id must be a UUID")
        if not isinstance(self.event_type, RecommendationAuditEventType):
            raise ValueError("event_type must be a supported audit event type")
        if not isinstance(self.review_status, RecommendationReviewStatus):
            raise ValueError("review_status must be a supported review status")
        if self.decision_id is not None and not isinstance(self.decision_id, UUID):
            raise ValueError("decision_id must be a UUID when present")
        _validate_positive_integer(self.sequence_number, "sequence_number")
        _validate_positive_integer(
            self.recommended_reorder_quantity,
            "recommended_reorder_quantity",
        )
        object.__setattr__(
            self,
            "occurred_at",
            _normalize_utc(self.occurred_at, "occurred_at"),
        )
        object.__setattr__(self, "actor", _normalize_optional_text(self.actor))
        object.__setattr__(self, "note", _normalize_optional_text(self.note))

        if self.event_type is RecommendationAuditEventType.REVIEW_CREATED:
            self._validate_creation_event()
        elif self.event_type is RecommendationAuditEventType.RECOMMENDATION_APPROVED:
            self._validate_approval_event()
        else:
            self._validate_rejection_event()

    def _validate_creation_event(self) -> None:
        if self.sequence_number != 1:
            raise ValueError("review_created must use sequence_number 1")
        if self.review_status is not RecommendationReviewStatus.PENDING_REVIEW:
            raise ValueError("review_created must record pending_review status")
        if any(
            value is not None
            for value in (
                self.decision_id,
                self.actor,
                self.approved_quantity,
                self.note,
            )
        ):
            raise ValueError("review_created must not contain decision details")

    def _validate_approval_event(self) -> None:
        if self.sequence_number != 2:
            raise ValueError("recommendation_approved must use sequence_number 2")
        if self.review_status is not RecommendationReviewStatus.APPROVED:
            raise ValueError("recommendation_approved must record approved status")
        if self.decision_id is None or self.actor is None:
            raise ValueError("recommendation_approved requires decision details")
        if self.approved_quantity is None:
            raise ValueError("recommendation_approved requires approved_quantity")
        _validate_positive_integer(self.approved_quantity, "approved_quantity")

    def _validate_rejection_event(self) -> None:
        if self.sequence_number != 2:
            raise ValueError("recommendation_rejected must use sequence_number 2")
        if self.review_status is not RecommendationReviewStatus.REJECTED:
            raise ValueError("recommendation_rejected must record rejected status")
        if self.decision_id is None or self.actor is None or self.note is None:
            raise ValueError("recommendation_rejected requires decision details")
        if self.approved_quantity is not None:
            raise ValueError("recommendation_rejected must not have approved_quantity")


def create_review_created_audit_event(
    *,
    event_id: UUID,
    review: ReorderRecommendationReview,
    sequence_number: int,
) -> RecommendationAuditEvent:
    """Create the first event for a valid pending review."""
    if (
        review.review_status is not RecommendationReviewStatus.PENDING_REVIEW
        or review.decision is not None
    ):
        raise ValueError("a creation event requires a pending review")
    return RecommendationAuditEvent(
        event_id=event_id,
        recommendation_id=review.recommendation_id,
        sequence_number=sequence_number,
        event_type=RecommendationAuditEventType.REVIEW_CREATED,
        occurred_at=review.created_at,
        review_status=review.review_status,
        decision_id=None,
        actor=None,
        recommended_reorder_quantity=(
            review.recommendation.recommended_reorder_quantity
        ),
        approved_quantity=None,
        note=None,
    )


def create_review_decision_audit_event(
    *,
    event_id: UUID,
    review: ReorderRecommendationReview,
    sequence_number: int,
) -> RecommendationAuditEvent:
    """Create an approval or rejection event from a terminal review."""
    decision = review.decision
    if (
        review.review_status is RecommendationReviewStatus.PENDING_REVIEW
        or decision is None
    ):
        raise ValueError("a decision event requires a terminal review")

    event_type = (
        RecommendationAuditEventType.RECOMMENDATION_APPROVED
        if decision.decision_type is RecommendationDecisionType.APPROVED
        else RecommendationAuditEventType.RECOMMENDATION_REJECTED
    )
    return RecommendationAuditEvent(
        event_id=event_id,
        recommendation_id=review.recommendation_id,
        sequence_number=sequence_number,
        event_type=event_type,
        occurred_at=decision.decided_at,
        review_status=review.review_status,
        decision_id=decision.decision_id,
        actor=decision.decided_by,
        recommended_reorder_quantity=(
            review.recommendation.recommended_reorder_quantity
        ),
        approved_quantity=decision.approved_quantity,
        note=decision.note,
    )
