"""Tests for pure deterministic baseline-demand forecasting."""

from datetime import date
from decimal import Decimal
from typing import cast
from uuid import UUID

import pytest

from opsmind.domain.demand import DemandObservation
from opsmind.domain.errors import InsufficientDemandHistoryError
from opsmind.domain.forecast import (
    BaselineForecast,
    ForecastMethod,
    calculate_simple_mean_forecast,
)

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000002")


def observation(
    demand_date: date,
    quantity: int,
    product_id: UUID = PRODUCT_ID,
) -> DemandObservation:
    """Create one immutable demand observation."""
    return DemandObservation(product_id, demand_date, quantity)


def calculate(
    observations: tuple[DemandObservation, ...],
    *,
    lookback: int = 7,
    horizon: int = 7,
    cutoff: date | None = None,
) -> BaselineForecast:
    """Calculate a forecast for the test product."""
    return calculate_simple_mean_forecast(
        product_id=PRODUCT_ID,
        observations=observations,
        lookback_observations=lookback,
        horizon_days=horizon,
        as_of_date=cutoff,
    )


def test_one_observation_forecast_contains_complete_metadata() -> None:
    demand_date = date(2026, 7, 1)

    result = calculate((observation(demand_date, 12),), lookback=4, horizon=3)

    assert result.product_id == PRODUCT_ID
    assert result.method is ForecastMethod.SIMPLE_MEAN
    assert result.as_of_date == demand_date
    assert result.lookback_observations_requested == 4
    assert result.observations_used == 1
    assert result.training_start_date == demand_date
    assert result.training_end_date == demand_date
    assert result.average_daily_demand == Decimal("12.00")
    assert result.horizon_days == 3
    assert result.forecast_quantity == Decimal("36.00")


def test_multiple_observation_mean_and_horizon_calculation() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 1), 12),
            observation(date(2026, 7, 2), 18),
            observation(date(2026, 7, 3), 9),
        ),
        horizon=7,
    )

    assert result.average_daily_demand == Decimal("13.00")
    assert result.forecast_quantity == Decimal("91.00")


def test_exact_mean_drives_forecast_before_independent_rounding() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 1), 1),
            observation(date(2026, 7, 2), 0),
            observation(date(2026, 7, 3), 0),
        ),
        horizon=3,
    )

    assert result.average_daily_demand == Decimal("0.33")
    assert result.forecast_quantity == Decimal("1.00")
    assert result.average_daily_demand.as_tuple().exponent == -2
    assert result.forecast_quantity.as_tuple().exponent == -2


def test_round_half_up_is_used_at_two_decimal_places() -> None:
    observations = tuple(
        observation(date(2026, 7, day), 1 if day == 1 else 0) for day in range(1, 9)
    )

    result = calculate(observations, lookback=8, horizon=1)

    assert result.average_daily_demand == Decimal("0.13")
    assert result.forecast_quantity == Decimal("0.13")


def test_recorded_zeroes_are_selected_and_all_zeroes_remain_zero() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 1), 0),
            observation(date(2026, 7, 3), 0),
        ),
        horizon=30,
    )

    assert result.observations_used == 2
    assert result.average_daily_demand == Decimal("0.00")
    assert result.forecast_quantity == Decimal("0.00")


def test_unsorted_input_selects_most_recent_observations_chronologically() -> None:
    observations = (
        observation(date(2026, 7, 10), 21),
        observation(date(2026, 7, 1), 12),
        observation(date(2026, 7, 4), 0),
        observation(date(2026, 7, 3), 9),
        observation(date(2026, 7, 2), 18),
    )

    result = calculate(observations, lookback=2, horizon=1)

    assert result.training_start_date == date(2026, 7, 4)
    assert result.training_end_date == date(2026, 7, 10)
    assert result.observations_used == 2
    assert result.average_daily_demand == Decimal("10.50")


def test_fewer_observations_than_requested_uses_all_without_imputing_dates() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 1), 12),
            observation(date(2026, 7, 10), 18),
        ),
        lookback=30,
        horizon=1,
    )

    assert result.lookback_observations_requested == 30
    assert result.observations_used == 2
    assert result.training_start_date == date(2026, 7, 1)
    assert result.training_end_date == date(2026, 7, 10)
    assert result.average_daily_demand == Decimal("15.00")


def test_explicit_cutoff_is_inclusive_and_excludes_later_observations() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 3), 9),
            observation(date(2026, 7, 4), 0),
            observation(date(2026, 7, 10), 99),
        ),
        cutoff=date(2026, 7, 4),
        horizon=1,
    )

    assert result.as_of_date == date(2026, 7, 4)
    assert result.training_end_date == date(2026, 7, 4)
    assert result.observations_used == 2
    assert result.average_daily_demand == Decimal("4.50")


def test_default_cutoff_is_latest_observation_without_using_system_clock() -> None:
    result = calculate(
        (
            observation(date(2001, 1, 1), 2),
            observation(date(2001, 1, 3), 4),
        ),
        horizon=1,
    )

    assert result.as_of_date == date(2001, 1, 3)


def test_no_observations_raises_insufficient_history_without_cutoff() -> None:
    with pytest.raises(InsufficientDemandHistoryError) as error:
        calculate(())

    assert error.value.product_id == PRODUCT_ID
    assert error.value.effective_cutoff is None
    assert str(error.value) == (
        "At least one demand observation is required to calculate a forecast for "
        f"product '{PRODUCT_ID}'."
    )


def test_cutoff_before_all_history_raises_with_effective_cutoff() -> None:
    cutoff = date(2026, 6, 30)

    with pytest.raises(InsufficientDemandHistoryError) as error:
        calculate(
            (observation(date(2026, 7, 1), 12),),
            cutoff=cutoff,
        )

    assert error.value.product_id == PRODUCT_ID
    assert error.value.effective_cutoff == cutoff
    assert str(error.value) == (
        f"No demand observations are available for product '{PRODUCT_ID}' on or "
        "before '2026-06-30'."
    )


@pytest.mark.parametrize(
    ("name", "lookback", "horizon", "message"),
    [
        ("zero lookback", 0, 7, "lookback_observations"),
        ("negative lookback", -1, 7, "lookback_observations"),
        ("excessive lookback", 366, 7, "lookback_observations"),
        ("zero horizon", 7, 0, "horizon_days"),
        ("negative horizon", 7, -1, "horizon_days"),
        ("excessive horizon", 7, 366, "horizon_days"),
    ],
)
def test_forecast_parameter_bounds(
    name: str,
    lookback: int,
    horizon: int,
    message: str,
) -> None:
    del name
    with pytest.raises(ValueError, match=rf"^{message} must be between 1 and 365$"):
        calculate(
            (observation(date(2026, 7, 1), 1),),
            lookback=lookback,
            horizon=horizon,
        )


@pytest.mark.parametrize(
    ("lookback", "horizon", "message"),
    [
        (cast(int, True), 7, "lookback_observations"),
        (7, cast(int, 1.5), "horizon_days"),
    ],
)
def test_forecast_parameters_require_integers(
    lookback: int,
    horizon: int,
    message: str,
) -> None:
    with pytest.raises(TypeError, match=rf"^{message} must be an integer$"):
        calculate(
            (observation(date(2026, 7, 1), 1),),
            lookback=lookback,
            horizon=horizon,
        )


def test_observations_must_belong_to_requested_product() -> None:
    with pytest.raises(
        ValueError,
        match=r"^observation product_id must match forecast product_id$",
    ):
        calculate((observation(date(2026, 7, 1), 1, OTHER_PRODUCT_ID),))


def test_input_is_unchanged_and_repeated_calls_are_equal() -> None:
    observations = (
        observation(date(2026, 7, 2), 18),
        observation(date(2026, 7, 1), 12),
    )
    original = tuple(observations)

    first = calculate(observations, lookback=2, horizon=7)
    second = calculate(observations, lookback=2, horizon=7)

    assert observations == original
    assert observations[0].demand_date == date(2026, 7, 2)
    assert first == second
