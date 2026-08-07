"""Pure temporal evaluation for the deterministic forecast baseline."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from opsmind.domain.forecast import (
    ForecastMethod,
    calculate_simple_mean_forecast,
    quantize_two_decimal_places,
)
from opsmind.evaluation.datasets import EvaluationSeries

MAX_EVALUATION_PARAMETER = 365


@dataclass(frozen=True, slots=True)
class EvaluationConfiguration:
    """Validated temporal evaluation settings."""

    lookback_observations: int = 7
    horizon_days: int = 7
    minimum_training_observations: int = 7

    def __post_init__(self) -> None:
        for name, value in (
            ("lookback_observations", self.lookback_observations),
            ("horizon_days", self.horizon_days),
            (
                "minimum_training_observations",
                self.minimum_training_observations,
            ),
        ):
            _validate_positive_integer(value, name)
        if self.minimum_training_observations > self.lookback_observations:
            raise ValueError(
                "minimum_training_observations must not exceed lookback_observations"
            )


class EvaluationExclusionReason(StrEnum):
    """Expected reasons a candidate temporal window cannot be evaluated."""

    INSUFFICIENT_TRAINING_OBSERVATIONS = "insufficient_training_observations"
    INCOMPLETE_TARGET_WINDOW = "incomplete_target_window"


@dataclass(frozen=True, slots=True)
class EvaluationExclusion:
    """One inspectable excluded candidate forecast window."""

    pattern_name: str
    product_id: UUID
    forecast_origin: date
    reason: EvaluationExclusionReason
    detail: str


@dataclass(frozen=True, slots=True)
class ForecastEvaluationWindow:
    """One valid forecast-versus-actual temporal comparison."""

    dataset_version: str
    pattern_name: str
    product_id: UUID
    forecast_method: ForecastMethod
    forecast_origin: date
    lookback_observations_requested: int
    observations_used: int
    training_start_date: date
    training_end_date: date
    target_start_date: date
    target_end_date: date
    horizon_days: int
    forecast_quantity: Decimal
    actual_quantity: Decimal
    signed_error: Decimal
    absolute_error: Decimal


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    """Aggregate metrics for zero or more valid windows."""

    window_count: int
    total_forecast_quantity: Decimal
    total_actual_quantity: Decimal
    total_signed_error: Decimal
    total_absolute_error: Decimal
    mean_absolute_error: Decimal | None
    forecast_bias: Decimal | None
    wape_percent: Decimal | None


@dataclass(frozen=True, slots=True)
class PatternMetrics:
    """Metrics for one named demand pattern."""

    pattern_name: str
    metrics: EvaluationMetrics


@dataclass(frozen=True, slots=True)
class ForecastEvaluationResult:
    """Complete deterministic evaluation result and diagnostics."""

    dataset_version: str
    configuration: EvaluationConfiguration
    series_count: int
    attempted_windows: int
    valid_windows: int
    excluded_windows: int
    metrics: EvaluationMetrics
    metrics_by_pattern: tuple[PatternMetrics, ...]
    windows: tuple[ForecastEvaluationWindow, ...]
    exclusions: tuple[EvaluationExclusion, ...]


def _validate_positive_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not 1 <= value <= MAX_EVALUATION_PARAMETER:
        raise ValueError(f"{name} must be between 1 and 365")


def _validated_series(series: EvaluationSeries) -> EvaluationSeries:
    pattern_name = series.pattern_name.strip()
    if not pattern_name:
        raise ValueError("pattern_name must not be blank")
    if not series.observations:
        raise ValueError(f"pattern '{pattern_name}' must contain observations")

    chronological = tuple(
        sorted(series.observations, key=lambda item: item.demand_date)
    )
    dates: set[date] = set()
    for observation in chronological:
        if observation.product_id != series.product_id:
            raise ValueError(
                f"pattern '{pattern_name}' contains a mismatched product_id"
            )
        if observation.demand_date in dates:
            raise ValueError(
                f"pattern '{pattern_name}' contains duplicate demand date "
                f"'{observation.demand_date.isoformat()}'"
            )
        dates.add(observation.demand_date)

    return EvaluationSeries(
        pattern_name=pattern_name,
        product_id=series.product_id,
        observations=chronological,
    )


def _validated_dataset(
    series: tuple[EvaluationSeries, ...],
) -> tuple[EvaluationSeries, ...]:
    if not series:
        raise ValueError("evaluation dataset must contain at least one series")

    validated = tuple(_validated_series(item) for item in series)
    pattern_names = [item.pattern_name for item in validated]
    if len(set(pattern_names)) != len(pattern_names):
        raise ValueError("evaluation dataset contains duplicate pattern names")

    product_ids = [item.product_id for item in validated]
    if len(set(product_ids)) != len(product_ids):
        raise ValueError("evaluation dataset contains duplicate product identifiers")

    return tuple(
        sorted(validated, key=lambda item: (item.pattern_name, str(item.product_id)))
    )


def calculate_evaluation_metrics(
    windows: tuple[ForecastEvaluationWindow, ...],
) -> EvaluationMetrics:
    """Calculate exact aggregate metrics and public rounded values."""
    window_count = len(windows)
    total_forecast = sum(
        (window.forecast_quantity for window in windows),
        start=Decimal("0"),
    )
    total_actual = sum(
        (window.actual_quantity for window in windows),
        start=Decimal("0"),
    )
    total_signed_error = sum(
        (window.signed_error for window in windows),
        start=Decimal("0"),
    )
    total_absolute_error = sum(
        (window.absolute_error for window in windows),
        start=Decimal("0"),
    )

    if window_count == 0:
        mean_absolute_error = None
        forecast_bias = None
    else:
        mean_absolute_error = quantize_two_decimal_places(
            total_absolute_error / Decimal(window_count)
        )
        forecast_bias = quantize_two_decimal_places(
            total_signed_error / Decimal(window_count)
        )

    if total_actual == 0:
        wape_percent = None
    else:
        wape_percent = quantize_two_decimal_places(
            total_absolute_error / total_actual * Decimal("100")
        )

    return EvaluationMetrics(
        window_count=window_count,
        total_forecast_quantity=quantize_two_decimal_places(total_forecast),
        total_actual_quantity=quantize_two_decimal_places(total_actual),
        total_signed_error=quantize_two_decimal_places(total_signed_error),
        total_absolute_error=quantize_two_decimal_places(total_absolute_error),
        mean_absolute_error=mean_absolute_error,
        forecast_bias=forecast_bias,
        wape_percent=wape_percent,
    )


def _evaluate_series(
    *,
    dataset_version: str,
    series: EvaluationSeries,
    configuration: EvaluationConfiguration,
) -> tuple[
    tuple[ForecastEvaluationWindow, ...],
    tuple[EvaluationExclusion, ...],
]:
    observations = series.observations
    observation_by_date = {
        observation.demand_date: observation for observation in observations
    }
    windows: list[ForecastEvaluationWindow] = []
    exclusions: list[EvaluationExclusion] = []

    for origin_observation in observations:
        forecast_origin = origin_observation.demand_date
        forecast = calculate_simple_mean_forecast(
            product_id=series.product_id,
            observations=observations,
            lookback_observations=configuration.lookback_observations,
            horizon_days=configuration.horizon_days,
            as_of_date=forecast_origin,
        )

        if forecast.observations_used < configuration.minimum_training_observations:
            exclusions.append(
                EvaluationExclusion(
                    pattern_name=series.pattern_name,
                    product_id=series.product_id,
                    forecast_origin=forecast_origin,
                    reason=(
                        EvaluationExclusionReason.INSUFFICIENT_TRAINING_OBSERVATIONS
                    ),
                    detail=(
                        f"used {forecast.observations_used} training observations; "
                        "requires at least "
                        f"{configuration.minimum_training_observations}"
                    ),
                )
            )
            continue

        target_start = forecast_origin + timedelta(days=1)
        target_end = forecast_origin + timedelta(days=configuration.horizon_days)
        target_dates = tuple(
            target_start + timedelta(days=offset)
            for offset in range(configuration.horizon_days)
        )
        missing_target_dates = tuple(
            target_date
            for target_date in target_dates
            if target_date not in observation_by_date
        )
        if missing_target_dates:
            exclusions.append(
                EvaluationExclusion(
                    pattern_name=series.pattern_name,
                    product_id=series.product_id,
                    forecast_origin=forecast_origin,
                    reason=EvaluationExclusionReason.INCOMPLETE_TARGET_WINDOW,
                    detail=(
                        "missing target dates: "
                        + ", ".join(
                            target_date.isoformat()
                            for target_date in missing_target_dates
                        )
                    ),
                )
            )
            continue

        if forecast.training_end_date > forecast_origin:
            raise RuntimeError("forecast training data extends beyond its origin")
        if forecast_origin >= target_start:
            raise RuntimeError("forecast target does not begin after its origin")

        actual_quantity = Decimal(
            sum(
                observation_by_date[target_date].quantity
                for target_date in target_dates
            )
        )
        signed_error = forecast.forecast_quantity - actual_quantity
        windows.append(
            ForecastEvaluationWindow(
                dataset_version=dataset_version,
                pattern_name=series.pattern_name,
                product_id=series.product_id,
                forecast_method=forecast.method,
                forecast_origin=forecast_origin,
                lookback_observations_requested=(
                    forecast.lookback_observations_requested
                ),
                observations_used=forecast.observations_used,
                training_start_date=forecast.training_start_date,
                training_end_date=forecast.training_end_date,
                target_start_date=target_start,
                target_end_date=target_end,
                horizon_days=forecast.horizon_days,
                forecast_quantity=forecast.forecast_quantity,
                actual_quantity=actual_quantity,
                signed_error=signed_error,
                absolute_error=abs(signed_error),
            )
        )

    return tuple(windows), tuple(exclusions)


def evaluate_baseline_forecast(
    *,
    dataset_version: str,
    series: tuple[EvaluationSeries, ...],
    configuration: EvaluationConfiguration,
) -> ForecastEvaluationResult:
    """Evaluate the production baseline across deterministic temporal windows."""
    normalized_dataset_version = dataset_version.strip()
    if not normalized_dataset_version:
        raise ValueError("dataset_version must not be blank")

    validated_series = _validated_dataset(series)
    all_windows: list[ForecastEvaluationWindow] = []
    all_exclusions: list[EvaluationExclusion] = []

    for item in validated_series:
        windows, exclusions = _evaluate_series(
            dataset_version=normalized_dataset_version,
            series=item,
            configuration=configuration,
        )
        all_windows.extend(windows)
        all_exclusions.extend(exclusions)

    ordered_windows = tuple(
        sorted(
            all_windows,
            key=lambda item: (
                item.pattern_name,
                str(item.product_id),
                item.forecast_origin,
            ),
        )
    )
    ordered_exclusions = tuple(
        sorted(
            all_exclusions,
            key=lambda item: (
                item.pattern_name,
                str(item.product_id),
                item.forecast_origin,
            ),
        )
    )

    metrics_by_pattern = tuple(
        PatternMetrics(
            pattern_name=item.pattern_name,
            metrics=calculate_evaluation_metrics(
                tuple(
                    window
                    for window in ordered_windows
                    if window.pattern_name == item.pattern_name
                )
            ),
        )
        for item in validated_series
    )
    attempted_windows = sum(len(item.observations) for item in validated_series)

    return ForecastEvaluationResult(
        dataset_version=normalized_dataset_version,
        configuration=configuration,
        series_count=len(validated_series),
        attempted_windows=attempted_windows,
        valid_windows=len(ordered_windows),
        excluded_windows=len(ordered_exclusions),
        metrics=calculate_evaluation_metrics(ordered_windows),
        metrics_by_pattern=metrics_by_pattern,
        windows=ordered_windows,
        exclusions=ordered_exclusions,
    )
