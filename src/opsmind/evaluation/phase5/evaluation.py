"""Scenario-conformance evaluation for deterministic Phase 5 behavior."""

from dataclasses import dataclass
from decimal import ROUND_CEILING
from enum import StrEnum
from uuid import UUID

from opsmind.domain.reorder import (
    ReorderRecommendation,
    ReorderRecommendationPolicy,
    ReorderRecommendationStatus,
    calculate_reorder_recommendation,
)
from opsmind.domain.stockout import (
    StockoutExposure,
    StockoutExposureStatus,
    calculate_stockout_exposure,
)
from opsmind.evaluation.phase5.scenarios import ExpectedOutcome, Phase5Scenario


class Phase5FailureKind(StrEnum):
    """Governed classes of Phase 5 conformance failure."""

    EXPECTED_OUTPUT_MISMATCH = "expected_output_mismatch"
    EVIDENCE_PRESERVATION = "evidence_preservation"
    ROUNDING_INVARIANT = "rounding_invariant"
    STATUS_INVARIANT = "status_invariant"


@dataclass(frozen=True, slots=True)
class Phase5Failure:
    """One deterministic conformance failure."""

    scenario_name: str
    kind: Phase5FailureKind
    message: str


@dataclass(frozen=True, slots=True)
class ScenarioEvaluation:
    """Evaluation result for one governed scenario."""

    scenario: Phase5Scenario
    exposure: StockoutExposure
    recommendation: ReorderRecommendation
    failures: tuple[Phase5Failure, ...]

    @property
    def passed(self) -> bool:
        """Return whether the scenario satisfies every governed check."""
        return not self.failures


@dataclass(frozen=True, slots=True)
class Phase5EvaluationSummary:
    """Aggregate conformance counts for one governed evaluation run."""

    scenario_count: int
    passed_scenario_count: int
    failed_scenario_count: int
    sufficient_count: int
    shortage_projected_count: int
    no_reorder_needed_count: int
    reorder_recommended_count: int
    expected_output_mismatch_count: int
    evidence_preservation_failure_count: int
    rounding_invariant_failure_count: int
    status_invariant_failure_count: int


@dataclass(frozen=True, slots=True)
class Phase5EvaluationResult:
    """Complete deterministic Phase 5 scenario-conformance result."""

    dataset_version: str
    scenario_results: tuple[ScenarioEvaluation, ...]
    summary: Phase5EvaluationSummary


_EXPECTED_FIELDS = (
    "as_of_date",
    "lookback_observations_requested",
    "observations_used",
    "training_start_date",
    "training_end_date",
    "average_daily_demand",
    "lead_time_days",
    "on_hand_quantity",
    "allocated_quantity",
    "available_inventory",
    "forecasted_lead_time_demand",
    "projected_inventory_balance",
    "projected_shortage_quantity",
)


def _validated_scenarios(
    scenarios: tuple[Phase5Scenario, ...],
) -> tuple[Phase5Scenario, ...]:
    if not scenarios:
        raise ValueError("Phase 5 evaluation requires at least one scenario")

    names: set[str] = set()
    product_ids: set[UUID] = set()
    validated: list[Phase5Scenario] = []
    for scenario in scenarios:
        name = scenario.scenario_name.strip()
        if not name:
            raise ValueError("scenario_name must not be blank")
        if name in names:
            raise ValueError(f"duplicate Phase 5 scenario name: {name}")
        if scenario.product_id in product_ids:
            raise ValueError(f"duplicate Phase 5 product id: {scenario.product_id}")
        if scenario.product.id != scenario.product_id:
            raise ValueError(f"scenario '{name}' has mismatched product id")
        if scenario.inventory.product_id != scenario.product_id:
            raise ValueError(f"scenario '{name}' has mismatched inventory product id")
        if not scenario.observations:
            raise ValueError(f"scenario '{name}' must contain demand observations")
        if any(
            observation.product_id != scenario.product_id
            for observation in scenario.observations
        ):
            raise ValueError(f"scenario '{name}' has mismatched demand product id")
        if scenario.lookback_observations < 1:
            raise ValueError(f"scenario '{name}' lookback must be positive")
        names.add(name)
        product_ids.add(scenario.product_id)
        validated.append(scenario)

    return tuple(sorted(validated, key=lambda scenario: scenario.scenario_name))


def _expected_output_failure(
    scenario: Phase5Scenario,
    exposure: StockoutExposure,
    recommendation: ReorderRecommendation,
) -> Phase5Failure | None:
    expected: ExpectedOutcome = scenario.expected
    pairs: list[tuple[str, object, object]] = [
        (name, getattr(exposure, name), getattr(expected, name))
        for name in _EXPECTED_FIELDS
    ]
    pairs.extend(
        [
            ("exposure_status", exposure.status, expected.exposure_status),
            (
                "recommendation_policy",
                recommendation.recommendation_policy,
                expected.recommendation_policy,
            ),
            (
                "recommendation_status",
                recommendation.recommendation_status,
                expected.recommendation_status,
            ),
            (
                "recommended_reorder_quantity",
                recommendation.recommended_reorder_quantity,
                expected.recommended_reorder_quantity,
            ),
        ]
    )
    mismatches = [
        f"{name}: actual={actual!r}, expected={wanted!r}"
        for name, actual, wanted in pairs
        if actual != wanted
    ]
    if not mismatches:
        return None
    return Phase5Failure(
        scenario.scenario_name,
        Phase5FailureKind.EXPECTED_OUTPUT_MISMATCH,
        "; ".join(mismatches),
    )


def _evidence_failure(
    scenario: Phase5Scenario,
    exposure: StockoutExposure,
    recommendation: ReorderRecommendation,
) -> Phase5Failure | None:
    mismatches = [
        name
        for name in _EXPECTED_FIELDS
        if getattr(exposure, name) != getattr(recommendation, name)
    ]
    if exposure.product_id != recommendation.product_id:
        mismatches.insert(0, "product_id")
    if not mismatches:
        return None
    return Phase5Failure(
        scenario.scenario_name,
        Phase5FailureKind.EVIDENCE_PRESERVATION,
        "recommendation changed exposure evidence: " + ", ".join(mismatches),
    )


def _rounding_failure(
    scenario: Phase5Scenario,
    exposure: StockoutExposure,
    recommendation: ReorderRecommendation,
) -> Phase5Failure | None:
    expected_quantity = int(
        exposure.projected_shortage_quantity.to_integral_value(rounding=ROUND_CEILING)
    )
    problems: list[str] = []
    if (
        recommendation.recommendation_policy
        is not ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING
    ):
        problems.append("recommendation policy is not projected_shortage_ceiling")
    if recommendation.recommended_reorder_quantity != expected_quantity:
        problems.append(
            "recommended quantity does not equal ROUND_CEILING(public shortage)"
        )
    if not problems:
        return None
    return Phase5Failure(
        scenario.scenario_name,
        Phase5FailureKind.ROUNDING_INVARIANT,
        "; ".join(problems),
    )


def _status_failure(
    scenario: Phase5Scenario,
    exposure: StockoutExposure,
    recommendation: ReorderRecommendation,
) -> Phase5Failure | None:
    problems: list[str] = []
    zero_shortage = exposure.projected_shortage_quantity.is_zero()

    if exposure.projected_inventory_balance >= 0:
        if exposure.status is not StockoutExposureStatus.SUFFICIENT:
            problems.append("non-negative balance must be sufficient")
        if not zero_shortage:
            problems.append("sufficient exposure must have zero shortage")
    else:
        if exposure.status is not StockoutExposureStatus.SHORTAGE_PROJECTED:
            problems.append("negative balance must be shortage_projected")
        if exposure.projected_shortage_quantity <= 0:
            problems.append("shortage_projected must have positive shortage")

    if zero_shortage:
        if recommendation.recommended_reorder_quantity != 0:
            problems.append("zero shortage must recommend zero units")
        if (
            recommendation.recommendation_status
            is not ReorderRecommendationStatus.NO_REORDER_NEEDED
        ):
            problems.append("zero shortage must report no_reorder_needed")
    else:
        if recommendation.recommended_reorder_quantity <= 0:
            problems.append("positive shortage must recommend positive units")
        if (
            recommendation.recommendation_status
            is not ReorderRecommendationStatus.REORDER_RECOMMENDED
        ):
            problems.append("positive shortage must report reorder_recommended")

    if not problems:
        return None
    return Phase5Failure(
        scenario.scenario_name,
        Phase5FailureKind.STATUS_INVARIANT,
        "; ".join(problems),
    )


def _evaluate_scenario(scenario: Phase5Scenario) -> ScenarioEvaluation:
    exposure = calculate_stockout_exposure(
        product_id=scenario.product_id,
        product=scenario.product,
        inventory=scenario.inventory,
        observations=scenario.observations,
        lookback_observations=scenario.lookback_observations,
        as_of_date=scenario.as_of_date,
    )
    recommendation = calculate_reorder_recommendation(
        exposure=exposure,
        unit_of_measure=scenario.product.unit_of_measure,
    )
    failures = tuple(
        failure
        for failure in (
            _expected_output_failure(scenario, exposure, recommendation),
            _evidence_failure(scenario, exposure, recommendation),
            _rounding_failure(scenario, exposure, recommendation),
            _status_failure(scenario, exposure, recommendation),
        )
        if failure is not None
    )
    return ScenarioEvaluation(scenario, exposure, recommendation, failures)


def _failure_count(
    results: tuple[ScenarioEvaluation, ...],
    kind: Phase5FailureKind,
) -> int:
    return sum(
        failure.kind is kind for result in results for failure in result.failures
    )


def evaluate_phase5_scenarios(
    *,
    dataset_version: str,
    scenarios: tuple[Phase5Scenario, ...],
) -> Phase5EvaluationResult:
    """Evaluate governed scenarios using existing production domain functions."""

    normalized_version = dataset_version.strip()
    if not normalized_version:
        raise ValueError("dataset_version must not be blank")

    validated = _validated_scenarios(scenarios)
    results = tuple(_evaluate_scenario(scenario) for scenario in validated)

    summary = Phase5EvaluationSummary(
        scenario_count=len(results),
        passed_scenario_count=sum(result.passed for result in results),
        failed_scenario_count=sum(not result.passed for result in results),
        sufficient_count=sum(
            result.exposure.status is StockoutExposureStatus.SUFFICIENT
            for result in results
        ),
        shortage_projected_count=sum(
            result.exposure.status is StockoutExposureStatus.SHORTAGE_PROJECTED
            for result in results
        ),
        no_reorder_needed_count=sum(
            result.recommendation.recommendation_status
            is ReorderRecommendationStatus.NO_REORDER_NEEDED
            for result in results
        ),
        reorder_recommended_count=sum(
            result.recommendation.recommendation_status
            is ReorderRecommendationStatus.REORDER_RECOMMENDED
            for result in results
        ),
        expected_output_mismatch_count=_failure_count(
            results, Phase5FailureKind.EXPECTED_OUTPUT_MISMATCH
        ),
        evidence_preservation_failure_count=_failure_count(
            results, Phase5FailureKind.EVIDENCE_PRESERVATION
        ),
        rounding_invariant_failure_count=_failure_count(
            results, Phase5FailureKind.ROUNDING_INVARIANT
        ),
        status_invariant_failure_count=_failure_count(
            results, Phase5FailureKind.STATUS_INVARIANT
        ),
    )
    return Phase5EvaluationResult(normalized_version, results, summary)
