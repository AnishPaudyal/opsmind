"""Pure deterministic baseline-demand forecasting."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum
from uuid import UUID

from opsmind.domain.demand import DemandObservation
from opsmind.domain.errors import InsufficientDemandHistoryError

MIN_FORECAST_PARAMETER = 1
MAX_FORECAST_PARAMETER = 365
TWO_DECIMAL_PLACES = Decimal("0.01")


class ForecastMethod(StrEnum):
    """Supported transparent forecast methods."""

    SIMPLE_MEAN = "simple_mean"


@dataclass(frozen=True, slots=True)
class SimpleMeanStatistics:
    """Exact simple-mean inputs shared by read-only analytical results."""

    product_id: UUID
    as_of_date: date
    lookback_observations_requested: int
    observations_used: int
    training_start_date: date
    training_end_date: date
    exact_average_daily_demand: Decimal


@dataclass(frozen=True, slots=True)
class BaselineForecast:
    """One explanatory simple-mean demand forecast."""

    product_id: UUID
    method: ForecastMethod
    as_of_date: date
    lookback_observations_requested: int
    observations_used: int
    training_start_date: date
    training_end_date: date
    average_daily_demand: Decimal
    horizon_days: int
    forecast_quantity: Decimal


def _validate_bounded_integer(value: int, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if not MIN_FORECAST_PARAMETER <= value <= MAX_FORECAST_PARAMETER:
        raise ValueError(f"{name} must be between 1 and 365")


def quantize_two_decimal_places(value: Decimal) -> Decimal:
    """Round a public decimal value and normalize signed zero."""
    quantized_value = value.quantize(
        TWO_DECIMAL_PLACES,
        rounding=ROUND_HALF_UP,
    )
    if quantized_value == 0:
        return Decimal("0.00")
    return quantized_value


def calculate_simple_mean_statistics(
    *,
    product_id: UUID,
    observations: tuple[DemandObservation, ...],
    lookback_observations: int,
    as_of_date: date | None = None,
) -> SimpleMeanStatistics:
    """Select eligible demand and return its exact arithmetic mean."""
    _validate_bounded_integer(lookback_observations, "lookback_observations")

    observations_snapshot = tuple(observations)
    for observation in observations_snapshot:
        if observation.product_id != product_id:
            raise ValueError("observation product_id must match forecast product_id")

    if as_of_date is None:
        if not observations_snapshot:
            raise InsufficientDemandHistoryError(product_id, None)
        effective_cutoff = max(
            observation.demand_date for observation in observations_snapshot
        )
    else:
        effective_cutoff = as_of_date

    eligible_observations = sorted(
        (
            observation
            for observation in observations_snapshot
            if observation.demand_date <= effective_cutoff
        ),
        key=lambda observation: observation.demand_date,
    )
    if not eligible_observations:
        raise InsufficientDemandHistoryError(product_id, effective_cutoff)

    selected_observations = eligible_observations[-lookback_observations:]
    exact_average = Decimal(
        sum(observation.quantity for observation in selected_observations)
    ) / Decimal(len(selected_observations))

    return SimpleMeanStatistics(
        product_id=product_id,
        as_of_date=effective_cutoff,
        lookback_observations_requested=lookback_observations,
        observations_used=len(selected_observations),
        training_start_date=selected_observations[0].demand_date,
        training_end_date=selected_observations[-1].demand_date,
        exact_average_daily_demand=exact_average,
    )


def calculate_simple_mean_forecast(
    *,
    product_id: UUID,
    observations: tuple[DemandObservation, ...],
    lookback_observations: int,
    horizon_days: int,
    as_of_date: date | None = None,
) -> BaselineForecast:
    """Calculate a read-only arithmetic-mean forecast from recent demand."""
    _validate_bounded_integer(lookback_observations, "lookback_observations")
    _validate_bounded_integer(horizon_days, "horizon_days")
    statistics = calculate_simple_mean_statistics(
        product_id=product_id,
        observations=observations,
        lookback_observations=lookback_observations,
        as_of_date=as_of_date,
    )
    exact_forecast = statistics.exact_average_daily_demand * Decimal(horizon_days)

    return BaselineForecast(
        product_id=statistics.product_id,
        method=ForecastMethod.SIMPLE_MEAN,
        as_of_date=statistics.as_of_date,
        lookback_observations_requested=(statistics.lookback_observations_requested),
        observations_used=statistics.observations_used,
        training_start_date=statistics.training_start_date,
        training_end_date=statistics.training_end_date,
        average_daily_demand=quantize_two_decimal_places(
            statistics.exact_average_daily_demand
        ),
        horizon_days=horizon_days,
        forecast_quantity=quantize_two_decimal_places(exact_forecast),
    )
