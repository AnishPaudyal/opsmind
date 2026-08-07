"""Deterministic JSON and Markdown reporting for Phase 5 evaluation."""

import json
from decimal import Decimal
from typing import Any

from opsmind.domain.reorder import ReorderRecommendation
from opsmind.domain.stockout import StockoutExposure
from opsmind.evaluation.phase5.evaluation import Phase5EvaluationResult
from opsmind.evaluation.phase5.scenarios import ExpectedOutcome, Phase5Scenario

DECISION_QUALITY_REASON = (
    "No governed operational outcome labels or optimization objective exist "
    "in Phase 5 scope."
)

EXPLICIT_EXCLUSIONS = (
    "calibrated_stockout_probability",
    "learned_stockout_prediction",
    "probabilistic_forecasting",
    "safety_stock_optimization",
    "service_level_optimization",
    "supplier_selection",
    "supplier_lead_time_optimization",
    "supplier_reliability",
    "cost_optimization",
    "pack_size_optimization",
    "minimum_order_quantities",
    "purchase_order_creation",
    "external_ordering",
    "inventory_reservation_or_mutation",
    "recommendation_approval_or_rejection_quality",
    "authentication_or_authorization",
    "aws_or_deployment",
    "production_readiness",
)


def _decimal_text(value: Decimal) -> str:
    return format(value, ".2f")


def _expected_payload(expected: ExpectedOutcome) -> dict[str, object]:
    return {
        "as_of_date": expected.as_of_date.isoformat(),
        "lookback_observations_requested": expected.lookback_observations_requested,
        "observations_used": expected.observations_used,
        "training_start_date": expected.training_start_date.isoformat(),
        "training_end_date": expected.training_end_date.isoformat(),
        "average_daily_demand": _decimal_text(expected.average_daily_demand),
        "lead_time_days": expected.lead_time_days,
        "on_hand_quantity": expected.on_hand_quantity,
        "allocated_quantity": expected.allocated_quantity,
        "available_inventory": expected.available_inventory,
        "forecasted_lead_time_demand": _decimal_text(
            expected.forecasted_lead_time_demand
        ),
        "projected_inventory_balance": _decimal_text(
            expected.projected_inventory_balance
        ),
        "projected_shortage_quantity": _decimal_text(
            expected.projected_shortage_quantity
        ),
        "exposure_status": expected.exposure_status.value,
        "recommendation_policy": expected.recommendation_policy.value,
        "recommendation_status": expected.recommendation_status.value,
        "recommended_reorder_quantity": expected.recommended_reorder_quantity,
    }


def _exposure_payload(exposure: StockoutExposure) -> dict[str, object]:
    return {
        "product_id": str(exposure.product_id),
        "forecast_method": exposure.forecast_method.value,
        "as_of_date": exposure.as_of_date.isoformat(),
        "lookback_observations_requested": exposure.lookback_observations_requested,
        "observations_used": exposure.observations_used,
        "training_start_date": exposure.training_start_date.isoformat(),
        "training_end_date": exposure.training_end_date.isoformat(),
        "average_daily_demand": _decimal_text(exposure.average_daily_demand),
        "lead_time_days": exposure.lead_time_days,
        "on_hand_quantity": exposure.on_hand_quantity,
        "allocated_quantity": exposure.allocated_quantity,
        "available_inventory": exposure.available_inventory,
        "forecasted_lead_time_demand": _decimal_text(
            exposure.forecasted_lead_time_demand
        ),
        "projected_inventory_balance": _decimal_text(
            exposure.projected_inventory_balance
        ),
        "projected_shortage_quantity": _decimal_text(
            exposure.projected_shortage_quantity
        ),
        "status": exposure.status.value,
    }


def _recommendation_payload(
    recommendation: ReorderRecommendation,
) -> dict[str, object]:
    return {
        "product_id": str(recommendation.product_id),
        "unit_of_measure": recommendation.unit_of_measure,
        "recommendation_policy": recommendation.recommendation_policy.value,
        "recommendation_status": recommendation.recommendation_status.value,
        "forecast_method": recommendation.forecast_method.value,
        "as_of_date": recommendation.as_of_date.isoformat(),
        "lookback_observations_requested": (
            recommendation.lookback_observations_requested
        ),
        "observations_used": recommendation.observations_used,
        "training_start_date": recommendation.training_start_date.isoformat(),
        "training_end_date": recommendation.training_end_date.isoformat(),
        "average_daily_demand": _decimal_text(recommendation.average_daily_demand),
        "lead_time_days": recommendation.lead_time_days,
        "on_hand_quantity": recommendation.on_hand_quantity,
        "allocated_quantity": recommendation.allocated_quantity,
        "available_inventory": recommendation.available_inventory,
        "forecasted_lead_time_demand": _decimal_text(
            recommendation.forecasted_lead_time_demand
        ),
        "projected_inventory_balance": _decimal_text(
            recommendation.projected_inventory_balance
        ),
        "projected_shortage_quantity": _decimal_text(
            recommendation.projected_shortage_quantity
        ),
        "recommended_reorder_quantity": recommendation.recommended_reorder_quantity,
    }


def _scenario_input_payload(scenario: Phase5Scenario) -> dict[str, object]:
    return {
        "product": {
            "id": str(scenario.product.id),
            "sku": scenario.product.sku,
            "name": scenario.product.name,
            "unit_of_measure": scenario.product.unit_of_measure,
            "lead_time_days": scenario.product.lead_time_days,
            "is_active": scenario.product.is_active,
        },
        "inventory": {
            "product_id": str(scenario.inventory.product_id),
            "on_hand_quantity": scenario.inventory.on_hand_quantity,
            "allocated_quantity": scenario.inventory.allocated_quantity,
            "available_quantity": scenario.inventory.available_quantity,
        },
        "lookback_observations": scenario.lookback_observations,
        "as_of_date": scenario.as_of_date.isoformat(),
        "demand_observations": [
            {
                "product_id": str(observation.product_id),
                "demand_date": observation.demand_date.isoformat(),
                "quantity": observation.quantity,
            }
            for observation in scenario.observations
        ],
    }


def result_to_dict(result: Phase5EvaluationResult) -> dict[str, Any]:
    """Convert a result to a stable JSON-compatible mapping."""

    summary = result.summary
    return {
        "evaluation": {
            "type": "deterministic_scenario_conformance",
            "phase": 5,
            "governed_issue": 50,
        },
        "dataset": {
            "version": result.dataset_version,
            "scenario_count": summary.scenario_count,
        },
        "summary": {
            "scenario_count": summary.scenario_count,
            "passed_scenario_count": summary.passed_scenario_count,
            "failed_scenario_count": summary.failed_scenario_count,
            "sufficient_count": summary.sufficient_count,
            "shortage_projected_count": summary.shortage_projected_count,
            "no_reorder_needed_count": summary.no_reorder_needed_count,
            "reorder_recommended_count": summary.reorder_recommended_count,
            "expected_output_mismatch_count": summary.expected_output_mismatch_count,
            "evidence_preservation_failure_count": (
                summary.evidence_preservation_failure_count
            ),
            "rounding_invariant_failure_count": (
                summary.rounding_invariant_failure_count
            ),
            "status_invariant_failure_count": summary.status_invariant_failure_count,
        },
        "decision_quality": {
            "measurement": "not_measured",
            "reason": DECISION_QUALITY_REASON,
            "unsupported_metrics": [
                "stockout_accuracy",
                "recommendation_accuracy",
                "precision",
                "recall",
                "business_uplift",
                "service_level_improvement",
                "cost_savings",
            ],
        },
        "explicit_exclusions": list(EXPLICIT_EXCLUSIONS),
        "scenarios": [
            {
                "scenario_name": item.scenario.scenario_name,
                "passed": item.passed,
                "input": _scenario_input_payload(item.scenario),
                "expected": _expected_payload(item.scenario.expected),
                "actual": {
                    "exposure": _exposure_payload(item.exposure),
                    "recommendation": _recommendation_payload(item.recommendation),
                },
                "failures": [
                    {"kind": failure.kind.value, "message": failure.message}
                    for failure in item.failures
                ],
            }
            for item in result.scenario_results
        ],
    }


def render_json(result: Phase5EvaluationResult) -> str:
    """Render stable machine-readable Phase 5 evidence."""
    return json.dumps(result_to_dict(result), indent=2, sort_keys=True) + "\n"


def render_markdown(result: Phase5EvaluationResult) -> str:
    """Render stable human-readable Phase 5 evidence."""

    summary = result.summary
    lines = [
        "# Phase 5 Stockout and Reorder Evaluation",
        "",
        f"- Dataset version: `{result.dataset_version}`",
        "- Evaluation type: deterministic scenario conformance",
        "- Governed by: Issue #50",
        "",
        "## Summary",
        "",
        "| Measure | Count |",
        "| --- | ---: |",
        f"| Scenarios | {summary.scenario_count} |",
        f"| Passed scenarios | {summary.passed_scenario_count} |",
        f"| Failed scenarios | {summary.failed_scenario_count} |",
        f"| `sufficient` | {summary.sufficient_count} |",
        f"| `shortage_projected` | {summary.shortage_projected_count} |",
        f"| `no_reorder_needed` | {summary.no_reorder_needed_count} |",
        f"| `reorder_recommended` | {summary.reorder_recommended_count} |",
        f"| Expected-output mismatches | {summary.expected_output_mismatch_count} |",
        (
            "| Evidence-preservation failures | "
            f"{summary.evidence_preservation_failure_count} |"
        ),
        (
            "| Rounding-invariant failures | "
            f"{summary.rounding_invariant_failure_count} |"
        ),
        f"| Status-invariant failures | {summary.status_invariant_failure_count} |",
        "",
        "## Scenario results",
        "",
        (
            "| Scenario | Exposure status | Public shortage | "
            "Reorder status | Quantity | Result |"
        ),
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for item in result.scenario_results:
        lines.append(
            "| "
            f"`{item.scenario.scenario_name}` | "
            f"`{item.exposure.status.value}` | "
            f"{_decimal_text(item.exposure.projected_shortage_quantity)} | "
            f"`{item.recommendation.recommendation_status.value}` | "
            f"{item.recommendation.recommended_reorder_quantity} | "
            f"{'PASS' if item.passed else 'FAIL'} |"
        )

    lines.extend(
        [
            "",
            "## Governed invariants",
            "",
            "- Recommendation evidence must exactly preserve the exposure evidence used.",
            (
                "- Non-negative public projected balance must produce "
                "`sufficient` and zero shortage."
            ),
            (
                "- Negative public projected balance must produce "
                "`shortage_projected` and positive shortage."
            ),
            (
                "- `projected_shortage_ceiling` applies `ROUND_CEILING` to the "
                "public two-decimal shortage."
            ),
            "- Zero shortage must produce zero units and `no_reorder_needed`.",
            (
                "- Positive shortage must produce positive whole units and "
                "`reorder_recommended`."
            ),
            "",
            "## Decision-quality limitation",
            "",
            "**Decision-quality measurement: Not measured**",
            "",
            DECISION_QUALITY_REASON,
            "",
            (
                "This report therefore does not claim stockout accuracy, "
                "recommendation accuracy, precision, recall, business uplift, "
                "service-level improvement, or cost savings."
            ),
            "",
            "## Explicit exclusions",
            "",
        ]
    )
    lines.extend(f"- `{item}`" for item in EXPLICIT_EXCLUSIONS)

    failures = [
        failure
        for scenario_result in result.scenario_results
        for failure in scenario_result.failures
    ]
    lines.extend(["", "## Failures", ""])
    if failures:
        lines.extend(
            f"- `{failure.scenario_name}` / `{failure.kind.value}`: {failure.message}"
            for failure in failures
        )
    else:
        lines.append("- None. Every governed scenario and invariant passed.")

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "A passing run establishes deterministic policy conformance for "
                "the governed synthetic scenarios. It does not establish that "
                "the policy is economically optimal or that it improves "
                "real-world stockout, service-level, supplier, or cost outcomes."
            ),
            "",
        ]
    )
    return "\n".join(lines)
