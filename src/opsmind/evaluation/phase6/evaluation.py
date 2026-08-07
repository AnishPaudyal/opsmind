"""Deterministic Phase 6 workflow-policy conformance evaluation."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from opsmind.domain.errors import (
    RecommendationReviewConflictError,
    RecommendationReviewNotFoundError,
)
from opsmind.domain.recommendation_audit import RecommendationAuditEvent
from opsmind.domain.recommendation_review import (
    ReorderRecommendationReview,
    create_recommendation_review,
)
from opsmind.domain.reorder import ReorderRecommendation
from opsmind.evaluation.phase6.scenarios import (
    CREATED_AT,
    DATASET_VERSION,
    DECIDED_AT,
    Phase6Scenario,
    ScenarioKind,
    build_phase6_dataset,
    build_recommendation,
    fixed_uuid,
)
from opsmind.repositories.in_memory_recommendation_workflow import (
    InMemoryRecommendationWorkflowRepository,
)


@dataclass(frozen=True, slots=True)
class Phase6ScenarioResult:
    """Observed conformance evidence for one governed scenario."""

    name: str
    kind: str
    passed: bool
    expected_review_status: str
    actual_review_status: str
    expected_decision_type: str | None
    actual_decision_type: str | None
    expected_approved_quantity: int | None
    actual_approved_quantity: int | None
    expected_event_types: tuple[str, ...]
    actual_event_types: tuple[str, ...]
    expected_sequences: tuple[int, ...]
    actual_sequences: tuple[int, ...]
    conflict_expected: bool
    conflict_observed: bool
    expected_output_match: bool
    snapshot_preserved: bool
    terminal_cardinality_valid: bool
    retry_idempotency_valid: bool
    conflict_no_mutation_valid: bool
    audit_order_valid: bool
    memory_isolation_valid: bool


@dataclass(frozen=True, slots=True)
class Phase6Evaluation:
    """Aggregate deterministic Phase 6 evaluation result."""

    dataset_version: str
    scenario_count: int
    passed_scenarios: int
    failed_scenarios: int
    approval_scenarios: int
    rejection_scenarios: int
    idempotent_retry_scenarios: int
    expected_conflict_scenarios: int
    expected_output_mismatches: int
    snapshot_preservation_failures: int
    terminal_cardinality_failures: int
    retry_idempotency_failures: int
    conflict_mutation_failures: int
    audit_order_failures: int
    memory_isolation_failures: int
    results: tuple[Phase6ScenarioResult, ...]


def recommendation_signature(
    recommendation: ReorderRecommendation,
) -> tuple[object, ...]:
    """Return every governed recommendation/evidence field in stable order."""
    return (
        recommendation.product_id,
        recommendation.unit_of_measure,
        recommendation.recommendation_policy,
        recommendation.recommendation_status,
        recommendation.forecast_method,
        recommendation.as_of_date,
        recommendation.lookback_observations_requested,
        recommendation.observations_used,
        recommendation.training_start_date,
        recommendation.training_end_date,
        recommendation.average_daily_demand,
        recommendation.lead_time_days,
        recommendation.on_hand_quantity,
        recommendation.allocated_quantity,
        recommendation.available_inventory,
        recommendation.forecasted_lead_time_demand,
        recommendation.projected_inventory_balance,
        recommendation.projected_shortage_quantity,
        recommendation.recommended_reorder_quantity,
    )


def _terminal_cardinality_valid(
    review: ReorderRecommendationReview,
    events: tuple[RecommendationAuditEvent, ...],
) -> bool:
    if review.review_status.value == "pending_review":
        return review.decision is None and len(events) == 1
    terminal_events = tuple(
        event
        for event in events
        if event.event_type.value
        in {"recommendation_approved", "recommendation_rejected"}
    )
    return (
        review.decision is not None and len(events) == 2 and len(terminal_events) == 1
    )


def _actual_decision_type(review: ReorderRecommendationReview) -> str | None:
    return None if review.decision is None else review.decision.decision_type.value


def _actual_approved_quantity(review: ReorderRecommendationReview) -> int | None:
    return None if review.decision is None else review.decision.approved_quantity


def _build_pending(
    scenario: Phase6Scenario,
    repository: InMemoryRecommendationWorkflowRepository,
) -> ReorderRecommendationReview:
    review = create_recommendation_review(
        recommendation_id=fixed_uuid(0x63000000, scenario.ordinal),
        recommendation=build_recommendation(),
        created_at=CREATED_AT,
    )
    return repository.create_review(
        review,
        event_id=fixed_uuid(0x64000000, scenario.ordinal),
    )


def _approve(
    scenario: Phase6Scenario,
    repository: InMemoryRecommendationWorkflowRepository,
    *,
    approved_quantity: int | None = None,
    actor: str = " Planner ",
    note: str | None = " Expedite replenishment ",
    decided_at: datetime = DECIDED_AT,
) -> ReorderRecommendationReview:
    return repository.approve_review(
        fixed_uuid(0x63000000, scenario.ordinal),
        decision_id=fixed_uuid(0x65000000, scenario.ordinal),
        event_id=fixed_uuid(0x66000000, scenario.ordinal),
        decided_by=actor,
        decided_at=decided_at,
        approved_quantity=approved_quantity,
        note=note,
    )


def _reject(
    scenario: Phase6Scenario,
    repository: InMemoryRecommendationWorkflowRepository,
    *,
    actor: str = " Planner ",
    reason: str = " Supplier delivery is already confirmed ",
    decided_at: datetime = DECIDED_AT,
) -> ReorderRecommendationReview:
    return repository.reject_review(
        fixed_uuid(0x63000000, scenario.ordinal),
        decision_id=fixed_uuid(0x67000000, scenario.ordinal),
        event_id=fixed_uuid(0x68000000, scenario.ordinal),
        decided_by=actor,
        decided_at=decided_at,
        reason=reason,
    )


def _evaluate_scenario(scenario: Phase6Scenario) -> Phase6ScenarioResult:
    repository = InMemoryRecommendationWorkflowRepository()
    initial = _build_pending(scenario, repository)
    initial_signature = recommendation_signature(initial.recommendation)

    conflict_observed = False
    retry_idempotency_valid = True
    conflict_no_mutation_valid = True
    memory_isolation_valid = True

    if scenario.kind is ScenarioKind.PENDING_CREATION:
        final = initial

    elif scenario.kind is ScenarioKind.APPROVAL_DEFAULT:
        final = _approve(scenario, repository)

    elif scenario.kind is ScenarioKind.APPROVAL_OVERRIDE:
        final = _approve(scenario, repository, approved_quantity=17)

    elif scenario.kind is ScenarioKind.REJECTION_NORMALIZED:
        final = _reject(scenario, repository)

    elif scenario.kind is ScenarioKind.APPROVAL_IDENTICAL_RETRY:
        authoritative = _approve(scenario, repository)
        original_history = repository.list_audit_events(initial.recommendation_id)
        final = repository.approve_review(
            initial.recommendation_id,
            decision_id=fixed_uuid(0x69000000, scenario.ordinal),
            event_id=fixed_uuid(0x6A000000, scenario.ordinal),
            decided_by="Planner",
            decided_at=DECIDED_AT + timedelta(hours=3),
            approved_quantity=19,
            note="Expedite replenishment",
        )
        retry_idempotency_valid = (
            final == authoritative
            and repository.list_audit_events(initial.recommendation_id)
            == original_history
            and final.decision is not None
            and authoritative.decision is not None
            and final.decision.decision_id == authoritative.decision.decision_id
            and final.decision.decided_at == authoritative.decision.decided_at
        )

    elif scenario.kind is ScenarioKind.APPROVAL_CHANGED_RETRY:
        authoritative = _approve(scenario, repository)
        original_history = repository.list_audit_events(initial.recommendation_id)
        try:
            repository.approve_review(
                initial.recommendation_id,
                decision_id=fixed_uuid(0x69000000, scenario.ordinal),
                event_id=fixed_uuid(0x6A000000, scenario.ordinal),
                decided_by="Planner",
                decided_at=DECIDED_AT + timedelta(hours=2),
                approved_quantity=20,
                note="Expedite replenishment",
            )
        except RecommendationReviewConflictError:
            conflict_observed = True
        final = repository.get_review(initial.recommendation_id)
        conflict_no_mutation_valid = (
            conflict_observed
            and final == authoritative
            and repository.list_audit_events(initial.recommendation_id)
            == original_history
        )

    elif scenario.kind is ScenarioKind.REJECTION_IDENTICAL_RETRY:
        authoritative = _reject(scenario, repository)
        original_history = repository.list_audit_events(initial.recommendation_id)
        final = repository.reject_review(
            initial.recommendation_id,
            decision_id=fixed_uuid(0x69000000, scenario.ordinal),
            event_id=fixed_uuid(0x6A000000, scenario.ordinal),
            decided_by="Planner",
            decided_at=DECIDED_AT + timedelta(hours=3),
            reason="Supplier delivery is already confirmed",
        )
        retry_idempotency_valid = (
            final == authoritative
            and repository.list_audit_events(initial.recommendation_id)
            == original_history
            and final.decision is not None
            and authoritative.decision is not None
            and final.decision.decision_id == authoritative.decision.decision_id
            and final.decision.decided_at == authoritative.decision.decided_at
        )

    elif scenario.kind is ScenarioKind.REJECTION_CHANGED_RETRY:
        authoritative = _reject(scenario, repository)
        original_history = repository.list_audit_events(initial.recommendation_id)
        try:
            repository.reject_review(
                initial.recommendation_id,
                decision_id=fixed_uuid(0x69000000, scenario.ordinal),
                event_id=fixed_uuid(0x6A000000, scenario.ordinal),
                decided_by="Planner",
                decided_at=DECIDED_AT + timedelta(hours=2),
                reason="Different reason",
            )
        except RecommendationReviewConflictError:
            conflict_observed = True
        final = repository.get_review(initial.recommendation_id)
        conflict_no_mutation_valid = (
            conflict_observed
            and final == authoritative
            and repository.list_audit_events(initial.recommendation_id)
            == original_history
        )

    elif scenario.kind is ScenarioKind.REJECTION_AFTER_APPROVAL:
        authoritative = _approve(scenario, repository)
        original_history = repository.list_audit_events(initial.recommendation_id)
        try:
            repository.reject_review(
                initial.recommendation_id,
                decision_id=fixed_uuid(0x69000000, scenario.ordinal),
                event_id=fixed_uuid(0x6A000000, scenario.ordinal),
                decided_by="Planner",
                decided_at=DECIDED_AT + timedelta(hours=2),
                reason="Changed direction",
            )
        except RecommendationReviewConflictError:
            conflict_observed = True
        final = repository.get_review(initial.recommendation_id)
        conflict_no_mutation_valid = (
            conflict_observed
            and final == authoritative
            and repository.list_audit_events(initial.recommendation_id)
            == original_history
        )

    elif scenario.kind is ScenarioKind.APPROVAL_AFTER_REJECTION:
        authoritative = _reject(scenario, repository)
        original_history = repository.list_audit_events(initial.recommendation_id)
        try:
            repository.approve_review(
                initial.recommendation_id,
                decision_id=fixed_uuid(0x69000000, scenario.ordinal),
                event_id=fixed_uuid(0x6A000000, scenario.ordinal),
                decided_by="Planner",
                decided_at=DECIDED_AT + timedelta(hours=2),
                approved_quantity=19,
                note="Changed direction",
            )
        except RecommendationReviewConflictError:
            conflict_observed = True
        final = repository.get_review(initial.recommendation_id)
        conflict_no_mutation_valid = (
            conflict_observed
            and final == authoritative
            and repository.list_audit_events(initial.recommendation_id)
            == original_history
        )

    elif scenario.kind is ScenarioKind.SAME_TIMESTAMP_ORDERING:
        final = _approve(scenario, repository, decided_at=CREATED_AT)

    elif scenario.kind is ScenarioKind.MEMORY_ISOLATION:
        second = InMemoryRecommendationWorkflowRepository()
        try:
            second.get_review(initial.recommendation_id)
        except RecommendationReviewNotFoundError:
            memory_isolation_valid = True
        else:
            memory_isolation_valid = False
        final = repository.get_review(initial.recommendation_id)

    else:
        raise AssertionError(f"Unhandled Phase 6 scenario kind: {scenario.kind}")

    events = repository.list_audit_events(initial.recommendation_id)
    actual_event_types = tuple(event.event_type.value for event in events)
    actual_sequences = tuple(event.sequence_number for event in events)
    snapshot_preserved = (
        recommendation_signature(final.recommendation) == initial_signature
    )
    terminal_cardinality_valid = _terminal_cardinality_valid(final, events)
    audit_order_valid = actual_sequences == scenario.expected.sequences

    expected_output_match = (
        final.review_status.value == scenario.expected.review_status
        and _actual_decision_type(final) == scenario.expected.decision_type
        and _actual_approved_quantity(final) == scenario.expected.approved_quantity
        and actual_event_types == scenario.expected.event_types
        and actual_sequences == scenario.expected.sequences
        and conflict_observed == scenario.expected.conflict_expected
    )

    passed = all(
        (
            expected_output_match,
            snapshot_preserved,
            terminal_cardinality_valid,
            retry_idempotency_valid,
            conflict_no_mutation_valid,
            audit_order_valid,
            memory_isolation_valid,
        )
    )

    return Phase6ScenarioResult(
        name=scenario.name,
        kind=scenario.kind.value,
        passed=passed,
        expected_review_status=scenario.expected.review_status,
        actual_review_status=final.review_status.value,
        expected_decision_type=scenario.expected.decision_type,
        actual_decision_type=_actual_decision_type(final),
        expected_approved_quantity=scenario.expected.approved_quantity,
        actual_approved_quantity=_actual_approved_quantity(final),
        expected_event_types=scenario.expected.event_types,
        actual_event_types=actual_event_types,
        expected_sequences=scenario.expected.sequences,
        actual_sequences=actual_sequences,
        conflict_expected=scenario.expected.conflict_expected,
        conflict_observed=conflict_observed,
        expected_output_match=expected_output_match,
        snapshot_preserved=snapshot_preserved,
        terminal_cardinality_valid=terminal_cardinality_valid,
        retry_idempotency_valid=retry_idempotency_valid,
        conflict_no_mutation_valid=conflict_no_mutation_valid,
        audit_order_valid=audit_order_valid,
        memory_isolation_valid=memory_isolation_valid,
    )


def evaluate_phase6(
    scenarios: Iterable[Phase6Scenario] | None = None,
) -> Phase6Evaluation:
    """Evaluate all governed Phase 6 deterministic scenarios."""
    resolved = tuple(build_phase6_dataset() if scenarios is None else scenarios)
    results = tuple(_evaluate_scenario(scenario) for scenario in resolved)

    return Phase6Evaluation(
        dataset_version=DATASET_VERSION,
        scenario_count=len(results),
        passed_scenarios=sum(result.passed for result in results),
        failed_scenarios=sum(not result.passed for result in results),
        approval_scenarios=sum(
            result.expected_review_status == "approved" for result in results
        ),
        rejection_scenarios=sum(
            result.expected_review_status == "rejected" for result in results
        ),
        idempotent_retry_scenarios=sum(
            scenario.idempotent_retry for scenario in resolved
        ),
        expected_conflict_scenarios=sum(
            scenario.expected.conflict_expected for scenario in resolved
        ),
        expected_output_mismatches=sum(
            not result.expected_output_match for result in results
        ),
        snapshot_preservation_failures=sum(
            not result.snapshot_preserved for result in results
        ),
        terminal_cardinality_failures=sum(
            not result.terminal_cardinality_valid for result in results
        ),
        retry_idempotency_failures=sum(
            not result.retry_idempotency_valid for result in results
        ),
        conflict_mutation_failures=sum(
            not result.conflict_no_mutation_valid for result in results
        ),
        audit_order_failures=sum(not result.audit_order_valid for result in results),
        memory_isolation_failures=sum(
            not result.memory_isolation_valid for result in results
        ),
        results=results,
    )
