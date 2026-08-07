"""Tests for deterministic Phase 4 baseline forecast evaluation."""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from opsmind.domain.demand import DemandObservation
from opsmind.evaluation.__main__ import main
from opsmind.evaluation.datasets import (
    DATASET_START_DATE,
    DATASET_VERSION,
    EvaluationSeries,
    build_phase4_dataset,
)
from opsmind.evaluation.forecast import (
    EvaluationConfiguration,
    EvaluationExclusionReason,
    ForecastEvaluationResult,
    evaluate_baseline_forecast,
)
from opsmind.evaluation.reporting import render_json, render_markdown


def _series(pattern_name: str) -> EvaluationSeries:
    return next(
        item for item in build_phase4_dataset() if item.pattern_name == pattern_name
    )


def _evaluate(
    *items: EvaluationSeries,
    configuration: EvaluationConfiguration | None = None,
) -> ForecastEvaluationResult:
    return evaluate_baseline_forecast(
        dataset_version=DATASET_VERSION,
        series=tuple(items),
        configuration=(
            EvaluationConfiguration() if configuration is None else configuration
        ),
    )


def _observation_triples(
    series: EvaluationSeries,
) -> tuple[tuple[UUID, date, int], ...]:
    return tuple(
        (
            observation.product_id,
            observation.demand_date,
            observation.quantity,
        )
        for observation in series.observations
    )


def test_dataset_is_versioned_complete_and_deterministic() -> None:
    first = build_phase4_dataset()
    second = build_phase4_dataset()

    assert DATASET_VERSION == "phase4-synthetic-v1"
    assert [item.pattern_name for item in first] == sorted(
        [
            "stable",
            "upward_trend",
            "downward_trend",
            "weekly_seasonal",
            "intermittent",
            "all_zero",
            "missing_calendar_dates",
            "short_history",
            "abrupt_upward_level_shift",
        ]
    )
    assert len({item.product_id for item in first}) == 9
    assert [_observation_triples(item) for item in first] == [
        _observation_triples(item) for item in second
    ]


def test_dataset_identifiers_dates_counts_and_patterns_are_stable() -> None:
    dataset = {item.pattern_name: item for item in build_phase4_dataset()}

    expected_ids = {
        "stable": "51000000-0000-0000-0000-000000000001",
        "upward_trend": "51000000-0000-0000-0000-000000000002",
        "downward_trend": "51000000-0000-0000-0000-000000000003",
        "weekly_seasonal": "51000000-0000-0000-0000-000000000004",
        "intermittent": "51000000-0000-0000-0000-000000000005",
        "all_zero": "51000000-0000-0000-0000-000000000006",
        "missing_calendar_dates": ("51000000-0000-0000-0000-000000000007"),
        "short_history": "51000000-0000-0000-0000-000000000008",
        "abrupt_upward_level_shift": ("51000000-0000-0000-0000-000000000009"),
    }
    expected_counts = {
        "stable": 35,
        "upward_trend": 35,
        "downward_trend": 35,
        "weekly_seasonal": 35,
        "intermittent": 35,
        "all_zero": 35,
        "missing_calendar_dates": 33,
        "short_history": 10,
        "abrupt_upward_level_shift": 35,
    }

    assert {
        name: str(item.product_id) for name, item in dataset.items()
    } == expected_ids
    assert {
        name: len(item.observations) for name, item in dataset.items()
    } == expected_counts
    assert all(
        item.observations[0].demand_date == DATASET_START_DATE
        for item in dataset.values()
    )

    quantities = {
        name: tuple(observation.quantity for observation in item.observations)
        for name, item in dataset.items()
    }

    assert quantities["stable"] == (10,) * 35
    assert quantities["upward_trend"][0] == 5
    assert quantities["upward_trend"][-1] == 22
    assert quantities["downward_trend"][0] == 25
    assert quantities["downward_trend"][-1] == 8
    assert quantities["weekly_seasonal"][:7] * 5 == (quantities["weekly_seasonal"])
    assert quantities["intermittent"][:7] * 5 == quantities["intermittent"]
    assert 0 in quantities["intermittent"]
    assert any(value > 0 for value in quantities["intermittent"])
    assert set(quantities["all_zero"]) == {0}
    assert quantities["short_history"] == (8,) * 10
    assert quantities["abrupt_upward_level_shift"] == ((5,) * 21 + (20,) * 14)

    missing_dates = {
        observation.demand_date
        for observation in dataset["missing_calendar_dates"].observations
    }
    assert DATASET_START_DATE + timedelta(days=12) not in missing_dates
    assert DATASET_START_DATE + timedelta(days=24) not in missing_dates


@pytest.mark.parametrize(
    ("kwargs", "error_type", "message"),
    [
        (
            {"lookback_observations": 0},
            ValueError,
            "lookback_observations must be between 1 and 365",
        ),
        (
            {"horizon_days": 366},
            ValueError,
            "horizon_days must be between 1 and 365",
        ),
        (
            {"minimum_training_observations": True},
            TypeError,
            "minimum_training_observations must be an integer",
        ),
        (
            {
                "lookback_observations": 3,
                "minimum_training_observations": 4,
            },
            ValueError,
            ("minimum_training_observations must not exceed lookback_observations"),
        ),
    ],
)
def test_configuration_rejects_invalid_values(
    kwargs: dict[str, object],
    error_type: type[Exception],
    message: str,
) -> None:
    with pytest.raises(error_type, match=f"^{message}$"):
        EvaluationConfiguration(**kwargs)  # type: ignore[arg-type]


def test_stable_pattern_has_exact_zero_error() -> None:
    result = _evaluate(_series("stable"))

    assert result.attempted_windows == 35
    assert result.valid_windows == 22
    assert result.excluded_windows == 13
    assert result.metrics.mean_absolute_error == Decimal("0.00")
    assert result.metrics.forecast_bias == Decimal("0.00")
    assert result.metrics.wape_percent == Decimal("0.00")
    assert all(
        window.forecast_quantity == window.actual_quantity == Decimal("70")
        for window in result.windows
    )


def test_all_zero_pattern_has_undefined_wape_without_falsifying_zero() -> None:
    result = _evaluate(_series("all_zero"))

    assert result.valid_windows == 22
    assert result.metrics.mean_absolute_error == Decimal("0.00")
    assert result.metrics.forecast_bias == Decimal("0.00")
    assert result.metrics.wape_percent is None


def test_short_history_preserves_inspectable_zero_valid_result() -> None:
    result = _evaluate(_series("short_history"))

    assert result.attempted_windows == 10
    assert result.valid_windows == 0
    assert result.excluded_windows == 10
    assert result.metrics.mean_absolute_error is None
    assert result.metrics.forecast_bias is None
    assert result.metrics.wape_percent is None
    assert {exclusion.reason for exclusion in result.exclusions} == {
        EvaluationExclusionReason.INSUFFICIENT_TRAINING_OBSERVATIONS,
        EvaluationExclusionReason.INCOMPLETE_TARGET_WINDOW,
    }


def test_every_valid_window_prevents_future_data_leakage() -> None:
    result = _evaluate(*build_phase4_dataset())

    assert result.valid_windows > 0
    assert all(
        window.training_end_date
        <= window.forecast_origin
        < window.target_start_date
        <= window.target_end_date
        for window in result.windows
    )


def test_full_dataset_measurements_are_exact_and_reproducible() -> None:
    result = _evaluate(*build_phase4_dataset())

    assert result.attempted_windows == 288
    assert result.valid_windows == 161
    assert result.excluded_windows == 127
    assert result.valid_windows + result.excluded_windows == result.attempted_windows
    assert result.metrics.window_count == 161
    assert result.metrics.total_forecast_quantity == Decimal("9617.00")
    assert result.metrics.total_actual_quantity == Decimal("10352.00")
    assert result.metrics.total_signed_error == Decimal("-735.00")
    assert result.metrics.total_absolute_error == Decimal("1813.00")
    assert result.metrics.mean_absolute_error == Decimal("11.26")
    assert result.metrics.forecast_bias == Decimal("-4.57")
    assert result.metrics.wape_percent == Decimal("17.51")

    by_pattern = {item.pattern_name: item.metrics for item in result.metrics_by_pattern}
    assert by_pattern["abrupt_upward_level_shift"].mean_absolute_error == Decimal(
        "33.41"
    )
    assert by_pattern["upward_trend"].forecast_bias == Decimal("-24.50")
    assert by_pattern["downward_trend"].forecast_bias == Decimal("24.50")
    assert by_pattern["all_zero"].wape_percent is None
    assert by_pattern["short_history"].window_count == 0


def test_missing_dates_are_excluded_but_recorded_zeroes_are_valid() -> None:
    result = _evaluate(
        _series("missing_calendar_dates"),
        _series("intermittent"),
    )

    missing_exclusions = [
        exclusion
        for exclusion in result.exclusions
        if exclusion.pattern_name == "missing_calendar_dates"
        and exclusion.reason is EvaluationExclusionReason.INCOMPLETE_TARGET_WINDOW
    ]
    intermittent_windows = [
        window for window in result.windows if window.pattern_name == "intermittent"
    ]

    assert missing_exclusions
    assert intermittent_windows
    assert any(window.actual_quantity > 0 for window in intermittent_windows)


def test_trends_expose_signed_bias_convention() -> None:
    result = _evaluate(
        _series("upward_trend"),
        _series("downward_trend"),
    )
    metrics = {item.pattern_name: item.metrics for item in result.metrics_by_pattern}

    assert metrics["upward_trend"].forecast_bias is not None
    assert metrics["upward_trend"].forecast_bias < 0
    assert metrics["downward_trend"].forecast_bias is not None
    assert metrics["downward_trend"].forecast_bias > 0


def test_dataset_validation_rejects_duplicate_dates() -> None:
    product_id = UUID("52000000-0000-0000-0000-000000000001")
    duplicate_date = date(2026, 1, 1)
    series = EvaluationSeries(
        pattern_name="duplicate",
        product_id=product_id,
        observations=(
            DemandObservation(product_id, duplicate_date, 1),
            DemandObservation(product_id, duplicate_date, 2),
        ),
    )

    with pytest.raises(
        ValueError,
        match="contains duplicate demand date",
    ):
        _evaluate(series)


def test_evaluation_does_not_mutate_input_series() -> None:
    source = _series("stable")
    before = _observation_triples(source)

    first = _evaluate(source)
    second = _evaluate(source)

    assert _observation_triples(source) == before
    assert first == second


def test_json_and_markdown_are_deterministic_and_explain_undefined_wape() -> None:
    result = _evaluate(
        _series("all_zero"),
        _series("stable"),
        _series("short_history"),
    )

    first_json = render_json(result)
    second_json = render_json(result)
    first_markdown = render_markdown(result)
    second_markdown = render_markdown(result)
    payload = json.loads(first_json)

    assert first_json == second_json
    assert first_markdown == second_markdown
    assert first_json.endswith("\n")
    assert first_markdown.endswith("\n")
    assert payload["dataset"]["version"] == DATASET_VERSION
    assert payload["exclusion_counts"] == {
        "incomplete_target_window": 18,
        "insufficient_training_observations": 18,
    }
    assert payload["exclusion_counts_by_pattern"]["short_history"] == {
        "incomplete_target_window": 4,
        "insufficient_training_observations": 6,
    }
    assert "### Exclusions by demand pattern" in first_markdown
    assert "Not defined: total actual demand is zero" in first_markdown
    assert "Not available: no valid windows" in first_markdown
    all_zero = next(
        item
        for item in payload["metrics_by_pattern"]
        if item["pattern_name"] == "all_zero"
    )
    assert all_zero["metrics"]["wape_percent"] is None
    assert "No production-readiness claim is supported." in first_markdown


def test_cli_writes_only_documented_artifacts_and_protects_overwrite(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = tmp_path / "evaluation"

    first_status = main(["--output-dir", str(output_dir)])
    first_output = capsys.readouterr()
    json_path = output_dir / "evaluation.json"
    markdown_path = output_dir / "evaluation.md"
    original_json = json_path.read_text(encoding="utf-8")

    second_status = main(["--output-dir", str(output_dir)])
    second_output = capsys.readouterr()
    forced_status = main(["--output-dir", str(output_dir), "--force"])
    forced_output = capsys.readouterr()

    assert first_status == 0
    assert first_output.err == ""
    assert str(json_path) in first_output.out
    assert str(markdown_path) in first_output.out
    assert sorted(path.name for path in output_dir.iterdir()) == [
        "evaluation.json",
        "evaluation.md",
    ]
    assert second_status == 2
    assert "refusing to overwrite" in second_output.err
    assert json_path.read_text(encoding="utf-8") == original_json
    assert forced_status == 0
    assert forced_output.err == ""


def test_cli_zero_valid_windows_writes_diagnostics_and_exits_one(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output_dir = tmp_path / "zero-valid"

    status = main(
        [
            "--output-dir",
            str(output_dir),
            "--lookback-observations",
            "365",
            "--horizon-days",
            "365",
            "--minimum-training-observations",
            "365",
        ]
    )
    output = capsys.readouterr()
    payload = json.loads((output_dir / "evaluation.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "evaluation.md").read_text(encoding="utf-8")

    assert status == 1
    assert "zero valid windows" in output.err
    assert payload["window_counts"]["valid"] == 0
    assert payload["metrics"]["mean_absolute_error"] is None
    assert payload["metrics"]["forecast_bias"] is None
    assert payload["metrics"]["wape_percent"] is None
    assert "## Invalid phase-gate evidence" in markdown
    assert "Not available: no valid windows" in markdown
