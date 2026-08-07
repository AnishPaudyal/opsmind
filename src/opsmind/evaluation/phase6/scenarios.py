"""Governed deterministic scenarios for the Phase 6 workflow evaluation."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.reorder import (
    ReorderRecommendation,
    ReorderRecommendationPolicy,
    ReorderRecommendationStatus,
)

DATASET_VERSION = "phase6-synthetic-v1"

CREATED_AT = datetime(2026, 8, 7, 16, 0, tzinfo=UTC)
DECIDED_AT = datetime(2026, 8, 7, 17, 0, tzinfo=UTC)

PRODUCT_ID = UUID("62000000-0000-0000-0000-000000000001")


class ScenarioKind(StrEnum):
    """Supported governed Phase 6 deterministic scenarios."""

    PENDING_CREATION = "pending_creation"
    APPROVAL_DEFAULT = "approval_default"
    APPROVAL_OVERRIDE = "approval_override"
    REJECTION_NORMALIZED = "rejection_normalized"
    APPROVAL_IDENTICAL_RETRY = "approval_identical_retry"
    APPROVAL_CHANGED_RETRY = "approval_changed_retry"
    REJECTION_IDENTICAL_RETRY = "rejection_identical_retry"
    REJECTION_CHANGED_RETRY = "rejection_changed_retry"
    REJECTION_AFTER_APPROVAL = "rejection_after_approval"
    APPROVAL_AFTER_REJECTION = "approval_after_rejection"
    SAME_TIMESTAMP_ORDERING = "same_timestamp_ordering"
    MEMORY_ISOLATION = "memory_isolation"


@dataclass(frozen=True, slots=True)
class Phase6ExpectedOutcome:
    """Independent public outcome expected from one governed scenario."""

    review_status: str
    decision_type: str | None
    approved_quantity: int | None
    event_types: tuple[str, ...]
    sequences: tuple[int, ...]
    conflict_expected: bool = False


@dataclass(frozen=True, slots=True)
class Phase6Scenario:
    """One deterministic Phase 6 scenario and its independent oracle."""

    name: str
    kind: ScenarioKind
    ordinal: int
    expected: Phase6ExpectedOutcome
    idempotent_retry: bool = False
    memory_isolation: bool = False


def fixed_uuid(prefix: int, ordinal: int) -> UUID:
    """Return one stable UUID without randomness or system state."""
    return UUID(f"{prefix:08x}-0000-0000-0000-{ordinal:012x}")


def build_recommendation() -> ReorderRecommendation:
    """Build the governed actionable recommendation/evidence fixture."""
    return ReorderRecommendation(
        product_id=PRODUCT_ID,
        unit_of_measure="units",
        recommendation_policy=(ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING),
        recommendation_status=ReorderRecommendationStatus.REORDER_RECOMMENDED,
        forecast_method=ForecastMethod.SIMPLE_MEAN,
        as_of_date=date(2026, 8, 7),
        lookback_observations_requested=7,
        observations_used=7,
        training_start_date=date(2026, 8, 1),
        training_end_date=date(2026, 8, 7),
        average_daily_demand=Decimal("2.50"),
        lead_time_days=7,
        on_hand_quantity=10,
        allocated_quantity=5,
        available_inventory=5,
        forecasted_lead_time_demand=Decimal("23.75"),
        projected_inventory_balance=Decimal("-18.75"),
        projected_shortage_quantity=Decimal("18.75"),
        recommended_reorder_quantity=19,
    )


def build_phase6_dataset() -> tuple[Phase6Scenario, ...]:
    """Return the complete deterministic Phase 6 scenario set."""
    pending = Phase6ExpectedOutcome(
        review_status="pending_review",
        decision_type=None,
        approved_quantity=None,
        event_types=("review_created",),
        sequences=(1,),
    )
    approved_default = Phase6ExpectedOutcome(
        review_status="approved",
        decision_type="approved",
        approved_quantity=19,
        event_types=("review_created", "recommendation_approved"),
        sequences=(1, 2),
    )
    approved_override = Phase6ExpectedOutcome(
        review_status="approved",
        decision_type="approved",
        approved_quantity=17,
        event_types=("review_created", "recommendation_approved"),
        sequences=(1, 2),
    )
    rejected = Phase6ExpectedOutcome(
        review_status="rejected",
        decision_type="rejected",
        approved_quantity=None,
        event_types=("review_created", "recommendation_rejected"),
        sequences=(1, 2),
    )
    approved_conflict = Phase6ExpectedOutcome(
        review_status="approved",
        decision_type="approved",
        approved_quantity=19,
        event_types=("review_created", "recommendation_approved"),
        sequences=(1, 2),
        conflict_expected=True,
    )
    rejected_conflict = Phase6ExpectedOutcome(
        review_status="rejected",
        decision_type="rejected",
        approved_quantity=None,
        event_types=("review_created", "recommendation_rejected"),
        sequences=(1, 2),
        conflict_expected=True,
    )

    return (
        Phase6Scenario(
            "pending_review_creation",
            ScenarioKind.PENDING_CREATION,
            1,
            pending,
        ),
        Phase6Scenario(
            "approval_uses_recommended_quantity",
            ScenarioKind.APPROVAL_DEFAULT,
            2,
            approved_default,
        ),
        Phase6Scenario(
            "approval_positive_override",
            ScenarioKind.APPROVAL_OVERRIDE,
            3,
            approved_override,
        ),
        Phase6Scenario(
            "rejection_normalizes_reason",
            ScenarioKind.REJECTION_NORMALIZED,
            4,
            rejected,
        ),
        Phase6Scenario(
            "identical_normalized_approval_retry",
            ScenarioKind.APPROVAL_IDENTICAL_RETRY,
            5,
            approved_default,
            idempotent_retry=True,
        ),
        Phase6Scenario(
            "changed_approval_retry_conflicts",
            ScenarioKind.APPROVAL_CHANGED_RETRY,
            6,
            approved_conflict,
        ),
        Phase6Scenario(
            "identical_normalized_rejection_retry",
            ScenarioKind.REJECTION_IDENTICAL_RETRY,
            7,
            rejected,
            idempotent_retry=True,
        ),
        Phase6Scenario(
            "changed_rejection_retry_conflicts",
            ScenarioKind.REJECTION_CHANGED_RETRY,
            8,
            rejected_conflict,
        ),
        Phase6Scenario(
            "rejection_after_approval_conflicts",
            ScenarioKind.REJECTION_AFTER_APPROVAL,
            9,
            approved_conflict,
        ),
        Phase6Scenario(
            "approval_after_rejection_conflicts",
            ScenarioKind.APPROVAL_AFTER_REJECTION,
            10,
            rejected_conflict,
        ),
        Phase6Scenario(
            "same_timestamp_sequence_ordering",
            ScenarioKind.SAME_TIMESTAMP_ORDERING,
            11,
            approved_default,
        ),
        Phase6Scenario(
            "memory_repository_isolation",
            ScenarioKind.MEMORY_ISOLATION,
            12,
            pending,
            memory_isolation=True,
        ),
    )
