"""Deterministic JSON and Markdown reporting for forecast evaluation."""

import json
from collections import Counter
from decimal import Decimal

from opsmind.evaluation.forecast import (
    EvaluationMetrics,
    ForecastEvaluationResult,
)


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return format(value, ".2f")


def _metrics_payload(metrics: EvaluationMetrics) -> dict[str, object]:
    return {
        "window_count": metrics.window_count,
        "total_forecast_quantity": _decimal_text(metrics.total_forecast_quantity),
        "total_actual_quantity": _decimal_text(metrics.total_actual_quantity),
        "total_signed_error": _decimal_text(metrics.total_signed_error),
        "total_absolute_error": _decimal_text(metrics.total_absolute_error),
        "mean_absolute_error": _decimal_text(metrics.mean_absolute_error),
        "forecast_bias": _decimal_text(metrics.forecast_bias),
        "wape_percent": _decimal_text(metrics.wape_percent),
    }


def _exclusion_counts_by_reason(
    result: ForecastEvaluationResult,
) -> dict[str, int]:
    """Return deterministic exclusion totals grouped by reason."""
    counts = Counter(exclusion.reason.value for exclusion in result.exclusions)
    return dict(sorted(counts.items()))


def _exclusion_counts_by_pattern(
    result: ForecastEvaluationResult,
) -> dict[str, dict[str, int]]:
    """Return deterministic exclusion totals grouped by pattern and reason."""
    pattern_names = sorted({exclusion.pattern_name for exclusion in result.exclusions})
    return {
        pattern_name: dict(
            sorted(
                Counter(
                    exclusion.reason.value
                    for exclusion in result.exclusions
                    if exclusion.pattern_name == pattern_name
                ).items()
            )
        )
        for pattern_name in pattern_names
    }


def result_to_dict(result: ForecastEvaluationResult) -> dict[str, object]:
    """Convert a complete result into deterministic JSON-compatible data."""
    return {
        "dataset": {
            "version": result.dataset_version,
            "series_count": result.series_count,
        },
        "configuration": {
            "lookback_observations": (result.configuration.lookback_observations),
            "horizon_days": result.configuration.horizon_days,
            "minimum_training_observations": (
                result.configuration.minimum_training_observations
            ),
            "signed_error_convention": "forecast_minus_actual",
            "metric_precision": "two_decimal_places_round_half_up",
        },
        "window_counts": {
            "attempted": result.attempted_windows,
            "valid": result.valid_windows,
            "excluded": result.excluded_windows,
        },
        "metrics": _metrics_payload(result.metrics),
        "metrics_by_pattern": [
            {
                "pattern_name": item.pattern_name,
                "metrics": _metrics_payload(item.metrics),
            }
            for item in result.metrics_by_pattern
        ],
        "exclusion_counts": _exclusion_counts_by_reason(result),
        "exclusion_counts_by_pattern": _exclusion_counts_by_pattern(result),
        "windows": [
            {
                "dataset_version": window.dataset_version,
                "pattern_name": window.pattern_name,
                "product_id": str(window.product_id),
                "forecast_method": window.forecast_method.value,
                "forecast_origin": window.forecast_origin.isoformat(),
                "lookback_observations_requested": (
                    window.lookback_observations_requested
                ),
                "observations_used": window.observations_used,
                "training_start_date": window.training_start_date.isoformat(),
                "training_end_date": window.training_end_date.isoformat(),
                "target_start_date": window.target_start_date.isoformat(),
                "target_end_date": window.target_end_date.isoformat(),
                "horizon_days": window.horizon_days,
                "forecast_quantity": _decimal_text(window.forecast_quantity),
                "actual_quantity": _decimal_text(window.actual_quantity),
                "signed_error": _decimal_text(window.signed_error),
                "absolute_error": _decimal_text(window.absolute_error),
            }
            for window in result.windows
        ],
        "exclusions": [
            {
                "pattern_name": exclusion.pattern_name,
                "product_id": str(exclusion.product_id),
                "forecast_origin": exclusion.forecast_origin.isoformat(),
                "reason": exclusion.reason.value,
                "detail": exclusion.detail,
            }
            for exclusion in result.exclusions
        ],
    }


def render_json(result: ForecastEvaluationResult) -> str:
    """Render deterministic pretty JSON ending with one newline."""
    return (
        json.dumps(
            result_to_dict(result),
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )


def _error_metric_display(
    metrics: EvaluationMetrics,
    value: Decimal | None,
) -> str:
    """Render MAE or bias while distinguishing unavailable evidence."""
    if metrics.window_count == 0:
        return "Not available: no valid windows"
    if value is None:
        raise ValueError("error metric is missing for valid evaluation windows")
    return format(value, ".2f")


def _wape_display(metrics: EvaluationMetrics) -> str:
    """Render WAPE with its exact undefined-denominator explanation."""
    if metrics.window_count == 0:
        return "Not available: no valid windows"
    if metrics.wape_percent is None:
        return "Not defined: total actual demand is zero"
    return format(metrics.wape_percent, ".2f")


def _pattern_metrics(
    result: ForecastEvaluationResult,
) -> dict[str, EvaluationMetrics]:
    return {item.pattern_name: item.metrics for item in result.metrics_by_pattern}


def render_markdown(result: ForecastEvaluationResult) -> str:
    """Render a deterministic human-readable evaluation report."""
    exclusion_counts = _exclusion_counts_by_reason(result)
    exclusion_counts_by_pattern = _exclusion_counts_by_pattern(result)
    pattern_metrics = _pattern_metrics(result)

    lines = [
        "# Phase 4 Baseline Forecast Evaluation",
        "",
        "## Dataset and configuration",
        "",
        f"- Dataset version: `{result.dataset_version}`",
        f"- Demand series: {result.series_count}",
        (f"- Lookback observations: {result.configuration.lookback_observations}"),
        f"- Forecast horizon: {result.configuration.horizon_days} calendar days",
        (
            "- Minimum training observations: "
            f"{result.configuration.minimum_training_observations}"
        ),
        "- Signed error convention: forecast minus actual",
        "",
        "## Window summary",
        "",
        f"- Attempted windows: {result.attempted_windows}",
        f"- Valid windows: {result.valid_windows}",
        f"- Excluded windows: {result.excluded_windows}",
        "",
        "## Aggregate metrics",
        "",
        "| Metric | Value |",
        "|---|---:|",
        (
            "| Mean Absolute Error | "
            f"{_error_metric_display(result.metrics, result.metrics.mean_absolute_error)} |"
        ),
        (
            f"| Forecast bias | {_error_metric_display(result.metrics, result.metrics.forecast_bias)} |"
        ),
        (f"| WAPE (%) | {_wape_display(result.metrics)} |"),
        "",
        "## Metrics by demand pattern",
        "",
        "| Pattern | Valid windows | MAE | Bias | WAPE (%) |",
        "|---|---:|---:|---:|---:|",
    ]

    for item in result.metrics_by_pattern:
        lines.append(
            "| "
            f"{item.pattern_name} | "
            f"{item.metrics.window_count} | "
            f"{_error_metric_display(item.metrics, item.metrics.mean_absolute_error)} | "
            f"{_error_metric_display(item.metrics, item.metrics.forecast_bias)} | "
            f"{_wape_display(item.metrics)} |"
        )

    lines.extend(
        [
            "",
            "## Exclusions",
            "",
        ]
    )
    if exclusion_counts:
        for reason, count in sorted(exclusion_counts.items()):
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "### Exclusions by demand pattern",
            "",
            "| Pattern | Excluded windows | Reasons |",
            "|---|---:|---|",
        ]
    )
    if exclusion_counts_by_pattern:
        for pattern_name, counts in exclusion_counts_by_pattern.items():
            reason_text = ", ".join(
                f"`{reason}`: {count}" for reason, count in counts.items()
            )
            lines.append(f"| {pattern_name} | {sum(counts.values())} | {reason_text} |")
    else:
        lines.append("| None | 0 | None |")

    lines.extend(
        [
            "",
            "## Observed baseline strengths",
            "",
        ]
    )
    for pattern_name in ("stable", "all_zero"):
        metrics = pattern_metrics.get(pattern_name)
        if metrics is not None:
            lines.append(
                f"- `{pattern_name}`: MAE "
                f"{_error_metric_display(metrics, metrics.mean_absolute_error)}, bias "
                f"{_error_metric_display(metrics, metrics.forecast_bias)}."
            )
    if not any(name in pattern_metrics for name in ("stable", "all_zero")):
        lines.append("- No designated strength pattern was evaluated.")

    lines.extend(
        [
            "",
            "## Observed baseline weaknesses and sensitivities",
            "",
        ]
    )
    sensitivity_patterns = (
        "upward_trend",
        "downward_trend",
        "weekly_seasonal",
        "intermittent",
        "abrupt_upward_level_shift",
    )
    for pattern_name in sensitivity_patterns:
        metrics = pattern_metrics.get(pattern_name)
        if metrics is not None:
            lines.append(
                f"- `{pattern_name}`: MAE "
                f"{_error_metric_display(metrics, metrics.mean_absolute_error)}, bias "
                f"{_error_metric_display(metrics, metrics.forecast_bias)}."
            )
    if not any(name in pattern_metrics for name in sensitivity_patterns):
        lines.append("- No designated sensitivity pattern was evaluated.")

    lines.extend(
        [
            "",
            "## Downstream implications",
            "",
            (
                "- Forecast error carries into stockout exposure and reorder "
                "recommendations because those capabilities reuse baseline "
                "forecast evidence."
            ),
            (
                "- Negative bias can understate projected demand; positive bias "
                "can overstate projected demand."
            ),
            (
                "- This evaluation does not independently establish downstream "
                "decision quality."
            ),
            "",
            "## Limitations",
            "",
            "- Results use deterministic synthetic data only.",
            "- Results do not prove real-world forecast accuracy.",
            "- The baseline provides no uncertainty or prediction interval.",
            "- WAPE is not defined when total actual demand is zero.",
            (
                "- Missing calendar dates are excluded from complete target "
                "windows rather than interpreted as zero demand."
            ),
            "- No production-readiness claim is supported.",
            "",
            "## Follow-up recommendations",
            "",
            ("- Preserve this simple mean as a transparent reference baseline."),
            (
                "- Evaluate a governed real operational dataset before making "
                "real-world accuracy claims."
            ),
            (
                "- Compare future candidate models against the same temporal "
                "windows and metrics."
            ),
            (
                "- Evaluate stockout and reorder decision quality separately "
                "during the applicable phase gates."
            ),
        ]
    )

    if result.valid_windows == 0:
        lines.extend(
            [
                "",
                "## Invalid phase-gate evidence",
                "",
                (
                    "No valid forecast windows were produced. Aggregate MAE, "
                    "bias, and WAPE are unavailable, and this result cannot "
                    "support Phase 4 completion."
                ),
            ]
        )

    return "\n".join(lines) + "\n"
