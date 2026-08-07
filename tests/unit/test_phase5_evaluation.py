"""Tests for governed deterministic Phase 5 scenario evaluation."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from opsmind.domain.reorder import ReorderRecommendationStatus
from opsmind.domain.stockout import StockoutExposureStatus
from opsmind.evaluation.phase5.__main__ import main
from opsmind.evaluation.phase5.evaluation import (
    Phase5EvaluationResult,
    Phase5FailureKind,
    evaluate_phase5_scenarios,
)
from opsmind.evaluation.phase5.reporting import (
    render_json,
    render_markdown,
    result_to_dict,
)
from opsmind.evaluation.phase5.scenarios import (
    DATASET_VERSION,
    Phase5Scenario,
    build_phase5_scenarios,
)


def evaluate() -> Phase5EvaluationResult:
    """Evaluate the canonical governed Phase 5 dataset."""
    return evaluate_phase5_scenarios(
        dataset_version=DATASET_VERSION,
        scenarios=build_phase5_scenarios(),
    )


def _governed_scenario_signature(scenario: Phase5Scenario) -> tuple[object, ...]:
    # Compare only fields that govern Phase 5 calculations and evidence.
    return (
        scenario.scenario_name,
        scenario.product_id,
        scenario.product.id,
        scenario.product.sku,
        scenario.product.name,
        scenario.product.unit_of_measure,
        scenario.product.lead_time_days,
        scenario.product.is_active,
        scenario.inventory.product_id,
        scenario.inventory.on_hand_quantity,
        scenario.inventory.allocated_quantity,
        tuple(
            (
                observation.product_id,
                observation.demand_date,
                observation.quantity,
            )
            for observation in scenario.observations
        ),
        scenario.lookback_observations,
        scenario.as_of_date,
        scenario.expected,
    )


def test_dataset_is_deterministic_named_and_unique() -> None:
    first = build_phase5_scenarios()
    second = build_phase5_scenarios()

    assert tuple(map(_governed_scenario_signature, first)) == tuple(
        map(_governed_scenario_signature, second)
    )
    assert DATASET_VERSION == "phase5-synthetic-v1"
    assert len(first) == 11
    assert len({item.scenario_name for item in first}) == 11
    assert len({item.product_id for item in first}) == 11
    assert tuple(item.scenario_name for item in first) == tuple(
        sorted(item.scenario_name for item in first)
    )


@pytest.mark.parametrize(
    ("scenario_name", "shortage", "quantity"),
    [
        ("exact_coverage_boundary", "0.00", 0),
        ("fractional_shortage", "18.75", 19),
        ("large_lead_time_shortage", "300.00", 300),
        ("negative_available_inventory", "5.00", 5),
        ("observation_count_lookback_missing_dates", "5.00", 5),
        ("small_fractional_shortage", "0.01", 1),
        ("sufficient_buffer", "0.00", 0),
        ("whole_unit_shortage", "20.00", 20),
        ("zero_lead_time", "0.00", 0),
    ],
)
def test_canonical_expected_shortage_and_reorder_quantity(
    scenario_name: str,
    shortage: str,
    quantity: int,
) -> None:
    scenarios = {
        scenario.scenario_name: scenario for scenario in build_phase5_scenarios()
    }
    expected = scenarios[scenario_name].expected
    assert format(expected.projected_shortage_quantity, ".2f") == shortage
    assert expected.recommended_reorder_quantity == quantity


def test_all_governed_scenarios_pass() -> None:
    result = evaluate()
    assert result.summary.scenario_count == 11
    assert result.summary.passed_scenario_count == 11
    assert result.summary.failed_scenario_count == 0
    assert result.summary.sufficient_count == 5
    assert result.summary.shortage_projected_count == 6
    assert result.summary.no_reorder_needed_count == 5
    assert result.summary.reorder_recommended_count == 6
    assert result.summary.expected_output_mismatch_count == 0
    assert result.summary.evidence_preservation_failure_count == 0
    assert result.summary.rounding_invariant_failure_count == 0
    assert result.summary.status_invariant_failure_count == 0


def test_cutoff_excludes_future_demand() -> None:
    result = evaluate()
    scenario_result = next(
        item
        for item in result.scenario_results
        if item.scenario.scenario_name == "cutoff_excludes_future_observation"
    )
    assert len(scenario_result.scenario.observations) == 5
    assert scenario_result.exposure.observations_used == 4
    assert scenario_result.exposure.training_end_date.isoformat() == "2026-07-04"
    assert format(scenario_result.exposure.average_daily_demand, ".2f") == "10.00"


def test_missing_dates_keep_observation_count_lookback() -> None:
    result = evaluate()
    scenario_result = next(
        item
        for item in result.scenario_results
        if item.scenario.scenario_name == "observation_count_lookback_missing_dates"
    )
    assert scenario_result.exposure.observations_used == 2
    assert scenario_result.exposure.training_start_date.isoformat() == "2026-07-10"
    assert scenario_result.exposure.training_end_date.isoformat() == "2026-07-20"
    assert format(scenario_result.exposure.average_daily_demand, ".2f") == "20.00"


def test_recorded_zero_demand_remains_valid_evidence() -> None:
    result = evaluate()
    scenario_result = next(
        item
        for item in result.scenario_results
        if item.scenario.scenario_name == "recorded_zero_demand"
    )
    assert scenario_result.exposure.observations_used == 4
    assert format(scenario_result.exposure.average_daily_demand, ".2f") == "0.00"
    assert scenario_result.exposure.status is StockoutExposureStatus.SUFFICIENT
    assert (
        scenario_result.recommendation.recommendation_status
        is ReorderRecommendationStatus.NO_REORDER_NEEDED
    )


def test_negative_available_inventory_is_preserved_as_evidence() -> None:
    result = evaluate()
    scenario_result = next(
        item
        for item in result.scenario_results
        if item.scenario.scenario_name == "negative_available_inventory"
    )
    assert scenario_result.exposure.available_inventory == -5
    assert scenario_result.recommendation.available_inventory == -5
    assert scenario_result.recommendation.recommended_reorder_quantity == 5


def test_identical_evaluations_produce_identical_governed_evidence() -> None:
    first = evaluate()
    second = evaluate()

    assert first.summary == second.summary
    assert render_json(first) == render_json(second)
    assert render_markdown(first) == render_markdown(second)


def test_corrupted_expected_output_is_reported_without_changing_policy() -> None:
    scenarios = list(build_phase5_scenarios())
    first = scenarios[0]
    scenarios[0] = replace(
        first,
        expected=replace(first.expected, recommended_reorder_quantity=999),
    )
    result = evaluate_phase5_scenarios(
        dataset_version=DATASET_VERSION,
        scenarios=tuple(scenarios),
    )
    assert result.summary.failed_scenario_count == 1
    assert result.summary.expected_output_mismatch_count == 1
    assert result.summary.evidence_preservation_failure_count == 0
    assert result.summary.rounding_invariant_failure_count == 0
    assert result.summary.status_invariant_failure_count == 0
    assert (
        result.scenario_results[0].failures[0].kind
        is Phase5FailureKind.EXPECTED_OUTPUT_MISMATCH
    )


def test_blank_dataset_version_fails_safely() -> None:
    with pytest.raises(ValueError, match="dataset_version must not be blank"):
        evaluate_phase5_scenarios(
            dataset_version=" ",
            scenarios=build_phase5_scenarios(),
        )


def test_empty_scenario_dataset_fails_safely() -> None:
    with pytest.raises(
        ValueError,
        match="Phase 5 evaluation requires at least one scenario",
    ):
        evaluate_phase5_scenarios(dataset_version=DATASET_VERSION, scenarios=())


def test_json_report_is_deterministic_and_explicit_about_limitations() -> None:
    result = evaluate()
    first = render_json(result)
    second = render_json(result)
    payload = json.loads(first)
    assert first == second
    assert payload["dataset"]["version"] == DATASET_VERSION
    assert payload["summary"]["passed_scenario_count"] == 11
    assert payload["summary"]["failed_scenario_count"] == 0
    assert payload["decision_quality"]["measurement"] == "not_measured"
    assert "stockout_accuracy" in payload["decision_quality"]["unsupported_metrics"]
    assert "supplier_selection" in payload["explicit_exclusions"]
    assert "purchase_order_creation" in payload["explicit_exclusions"]


def test_json_report_contains_reproducible_scenario_inputs() -> None:
    payload = result_to_dict(evaluate())
    scenarios = {item["scenario_name"]: item for item in payload["scenarios"]}
    fractional = scenarios["fractional_shortage"]
    assert fractional["input"]["lookback_observations"] == 4
    assert fractional["input"]["as_of_date"] == "2026-07-04"
    assert len(fractional["input"]["demand_observations"]) == 4
    assert fractional["expected"]["projected_shortage_quantity"] == "18.75"
    assert fractional["actual"]["recommendation"]["recommended_reorder_quantity"] == 19


def test_markdown_report_states_conformance_not_business_accuracy() -> None:
    markdown = render_markdown(evaluate())
    assert "**Decision-quality measurement: Not measured**" in markdown
    assert "Every governed scenario and invariant passed." in markdown
    assert "does not establish that the policy is economically optimal" in markdown
    assert "| `fractional_shortage` | `shortage_projected` | 18.75 |" in markdown


def test_cli_writes_deterministic_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "phase5"
    assert main(["--output-dir", str(output_dir)]) == 0
    json_path = output_dir / "phase5-evaluation.json"
    markdown_path = output_dir / "phase5-evaluation.md"
    assert json_path.read_text(encoding="utf-8") == render_json(evaluate())
    assert markdown_path.read_text(encoding="utf-8") == render_markdown(evaluate())


def test_cli_refuses_to_overwrite_existing_artifacts(tmp_path: Path) -> None:
    output_dir = tmp_path / "phase5"
    assert main(["--output-dir", str(output_dir)]) == 0
    assert main(["--output-dir", str(output_dir)]) == 2
