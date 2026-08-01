"""Tests for pure deterministic stockout-exposure calculations."""

from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from opsmind.domain.demand import DemandObservation
from opsmind.domain.errors import InsufficientDemandHistoryError
from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
from opsmind.domain.stockout import (
    StockoutExposure,
    StockoutExposureStatus,
    calculate_stockout_exposure,
)

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000002")


def make_product(
    lead_time_days: int = 5,
    product_id: UUID = PRODUCT_ID,
) -> Product:
    """Create one immutable product for direct domain tests."""
    return Product(
        id=product_id,
        sku="SENSOR-001",
        name="Temperature Sensor",
        unit_of_measure="each",
        lead_time_days=lead_time_days,
        is_active=True,
    )


def make_inventory(
    on_hand_quantity: int = 60,
    allocated_quantity: int = 10,
    product_id: UUID = PRODUCT_ID,
) -> InventoryPosition:
    """Create one immutable inventory position."""
    return InventoryPosition(
        product_id=product_id,
        on_hand_quantity=on_hand_quantity,
        allocated_quantity=allocated_quantity,
    )


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
    product: Product | None = None,
    inventory: InventoryPosition | None = None,
    requested_product_id: UUID = PRODUCT_ID,
    lookback: int = 7,
    cutoff: date | None = None,
) -> StockoutExposure:
    """Calculate exposure with deterministic defaults."""
    return calculate_stockout_exposure(
        product_id=requested_product_id,
        product=product if product is not None else make_product(),
        inventory=inventory if inventory is not None else make_inventory(),
        observations=observations,
        lookback_observations=lookback,
        as_of_date=cutoff,
    )


def standard_demand() -> tuple[DemandObservation, ...]:
    """Return the issue's July 1 through July 4 demand window."""
    return (
        observation(date(2026, 7, 1), 12),
        observation(date(2026, 7, 2), 18),
        observation(date(2026, 7, 3), 9),
        observation(date(2026, 7, 4), 0),
    )


def test_positive_balance_result_contains_complete_explanatory_metadata() -> None:
    result = calculate(standard_demand(), lookback=4)

    assert result.product_id == PRODUCT_ID
    assert result.forecast_method is ForecastMethod.SIMPLE_MEAN
    assert result.as_of_date == date(2026, 7, 4)
    assert result.lookback_observations_requested == 4
    assert result.observations_used == 4
    assert result.training_start_date == date(2026, 7, 1)
    assert result.training_end_date == date(2026, 7, 4)
    assert result.average_daily_demand == Decimal("9.75")
    assert result.lead_time_days == 5
    assert result.on_hand_quantity == 60
    assert result.allocated_quantity == 10
    assert result.available_inventory == 50
    assert result.forecasted_lead_time_demand == Decimal("48.75")
    assert result.projected_inventory_balance == Decimal("1.25")
    assert result.projected_shortage_quantity == Decimal("0.00")
    assert result.status is StockoutExposureStatus.SUFFICIENT


def test_exact_zero_balance_is_sufficient_with_zero_shortage() -> None:
    result = calculate(
        (observation(date(2026, 7, 1), 10),),
        inventory=make_inventory(60, 10),
    )

    assert result.forecasted_lead_time_demand == Decimal("50.00")
    assert result.projected_inventory_balance == Decimal("0.00")
    assert result.projected_shortage_quantity == Decimal("0.00")
    assert result.status is StockoutExposureStatus.SUFFICIENT


def test_negative_balance_produces_matching_shortage_and_status() -> None:
    result = calculate(
        standard_demand(),
        inventory=make_inventory(40, 10),
        lookback=4,
    )

    assert result.available_inventory == 30
    assert result.projected_inventory_balance == Decimal("-18.75")
    assert result.projected_shortage_quantity == Decimal("18.75")
    assert result.status is StockoutExposureStatus.SHORTAGE_PROJECTED


def test_negative_available_inventory_is_preserved() -> None:
    result = calculate(
        (observation(date(2026, 7, 1), 2),),
        inventory=make_inventory(20, 30),
    )

    assert result.available_inventory == -10
    assert result.forecasted_lead_time_demand == Decimal("10.00")
    assert result.projected_inventory_balance == Decimal("-20.00")
    assert result.projected_shortage_quantity == Decimal("20.00")
    assert result.status is StockoutExposureStatus.SHORTAGE_PROJECTED


@pytest.mark.parametrize(
    (
        "on_hand_quantity",
        "allocated_quantity",
        "expected_balance",
        "expected_shortage",
        "expected_status",
    ),
    [
        (20, 10, Decimal("10.00"), Decimal("0.00"), "sufficient"),
        (10, 10, Decimal("0.00"), Decimal("0.00"), "sufficient"),
        (10, 20, Decimal("-10.00"), Decimal("10.00"), "shortage_projected"),
    ],
)
def test_zero_lead_time_uses_only_current_available_inventory(
    on_hand_quantity: int,
    allocated_quantity: int,
    expected_balance: Decimal,
    expected_shortage: Decimal,
    expected_status: str,
) -> None:
    result = calculate(
        (observation(date(2026, 7, 1), 99),),
        product=make_product(lead_time_days=0),
        inventory=make_inventory(on_hand_quantity, allocated_quantity),
    )

    assert result.lead_time_days == 0
    assert result.forecasted_lead_time_demand == Decimal("0.00")
    assert result.projected_inventory_balance == expected_balance
    assert result.projected_shortage_quantity == expected_shortage
    assert result.status.value == expected_status


def test_one_day_lead_time_uses_fractional_exact_average() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 1), 1),
            observation(date(2026, 7, 3), 2),
        ),
        product=make_product(lead_time_days=1),
        inventory=make_inventory(10, 0),
    )

    assert result.average_daily_demand == Decimal("1.50")
    assert result.forecasted_lead_time_demand == Decimal("1.50")
    assert result.projected_inventory_balance == Decimal("8.50")


def test_large_product_lead_time_above_365_is_not_capped() -> None:
    result = calculate(
        (observation(date(2026, 7, 1), 2),),
        product=make_product(lead_time_days=500),
        inventory=make_inventory(1200, 0),
    )

    assert result.lead_time_days == 500
    assert result.forecasted_lead_time_demand == Decimal("1000.00")
    assert result.projected_inventory_balance == Decimal("200.00")


def test_exact_mean_drives_lead_time_demand_before_rounding() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 1), 1),
            observation(date(2026, 7, 2), 0),
            observation(date(2026, 7, 3), 0),
        ),
        product=make_product(lead_time_days=3),
        inventory=make_inventory(1, 0),
    )

    assert result.average_daily_demand == Decimal("0.33")
    assert result.forecasted_lead_time_demand == Decimal("1.00")
    assert result.projected_inventory_balance == Decimal("0.00")
    assert result.status is StockoutExposureStatus.SUFFICIENT


def test_round_half_up_applies_at_the_public_boundary() -> None:
    observations = tuple(
        observation(date(2026, 7, day), 1 if day == 1 else 0) for day in range(1, 9)
    )

    result = calculate(
        observations,
        product=make_product(lead_time_days=1),
        inventory=make_inventory(1, 0),
        lookback=8,
    )

    assert result.average_daily_demand == Decimal("0.13")
    assert result.forecasted_lead_time_demand == Decimal("0.13")
    assert result.projected_inventory_balance == Decimal("0.88")


def test_negative_zero_is_normalized_before_shortage_and_status() -> None:
    first_date = date(2025, 1, 1)
    observations = tuple(
        observation(
            first_date + timedelta(days=index),
            1 if index == 0 else 0,
        )
        for index in range(365)
    )

    result = calculate(
        observations,
        product=make_product(lead_time_days=1),
        inventory=make_inventory(0, 0),
        lookback=365,
    )

    assert result.average_daily_demand == Decimal("0.00")
    assert result.forecasted_lead_time_demand == Decimal("0.00")
    assert result.projected_inventory_balance == Decimal("0.00")
    assert result.projected_inventory_balance.as_tuple().sign == 0
    assert result.projected_shortage_quantity == Decimal("0.00")
    assert result.projected_shortage_quantity.as_tuple().sign == 0
    assert result.status is StockoutExposureStatus.SUFFICIENT


def test_recorded_zeroes_and_all_zero_history_remain_real_observations() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 1), 0),
            observation(date(2026, 7, 10), 0),
        ),
        product=make_product(lead_time_days=30),
        inventory=make_inventory(0, 0),
    )

    assert result.observations_used == 2
    assert result.training_start_date == date(2026, 7, 1)
    assert result.training_end_date == date(2026, 7, 10)
    assert result.forecasted_lead_time_demand == Decimal("0.00")
    assert result.projected_inventory_balance == Decimal("0.00")


def test_cutoff_is_inclusive_and_excludes_future_observations() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 10), 100),
            observation(date(2026, 7, 1), 12),
            observation(date(2026, 7, 4), 0),
            observation(date(2026, 7, 3), 9),
            observation(date(2026, 7, 2), 18),
        ),
        product=make_product(lead_time_days=2),
        inventory=make_inventory(100, 0),
        lookback=2,
        cutoff=date(2026, 7, 3),
    )

    assert result.as_of_date == date(2026, 7, 3)
    assert result.training_start_date == date(2026, 7, 2)
    assert result.training_end_date == date(2026, 7, 3)
    assert result.observations_used == 2
    assert result.average_daily_demand == Decimal("13.50")
    assert result.forecasted_lead_time_demand == Decimal("27.00")


def test_latest_date_is_default_and_missing_dates_are_not_imputed() -> None:
    result = calculate(
        (
            observation(date(2026, 7, 1), 12),
            observation(date(2026, 7, 10), 18),
        ),
        product=make_product(lead_time_days=1),
        inventory=make_inventory(100, 0),
        lookback=30,
    )

    assert result.as_of_date == date(2026, 7, 10)
    assert result.lookback_observations_requested == 30
    assert result.observations_used == 2
    assert result.average_daily_demand == Decimal("15.00")


def test_no_observations_reuses_insufficient_history_error() -> None:
    with pytest.raises(InsufficientDemandHistoryError) as error:
        calculate(())

    assert error.value.product_id == PRODUCT_ID
    assert error.value.effective_cutoff is None


def test_cutoff_before_history_reuses_insufficient_history_error() -> None:
    cutoff = date(2026, 6, 30)

    with pytest.raises(InsufficientDemandHistoryError) as error:
        calculate(
            (observation(date(2026, 7, 1), 12),),
            cutoff=cutoff,
        )

    assert error.value.product_id == PRODUCT_ID
    assert error.value.effective_cutoff == cutoff


def test_requested_product_must_match_product() -> None:
    with pytest.raises(
        ValueError,
        match=r"^product id must match requested product_id$",
    ):
        calculate(
            (observation(date(2026, 7, 1), 1),),
            product=make_product(product_id=OTHER_PRODUCT_ID),
        )


def test_requested_product_must_match_inventory() -> None:
    with pytest.raises(
        ValueError,
        match=r"^inventory product_id must match requested product_id$",
    ):
        calculate(
            (observation(date(2026, 7, 1), 1),),
            inventory=make_inventory(product_id=OTHER_PRODUCT_ID),
        )


def test_requested_product_must_match_every_observation() -> None:
    with pytest.raises(
        ValueError,
        match=r"^observation product_id must match forecast product_id$",
    ):
        calculate((observation(date(2026, 7, 1), 1, OTHER_PRODUCT_ID),))


def test_inputs_remain_unchanged_and_repeated_calls_are_equal() -> None:
    product = make_product()
    inventory = make_inventory()
    observations = (
        observation(date(2026, 7, 2), 18),
        observation(date(2026, 7, 1), 12),
    )
    original_observations = tuple(observations)

    first = calculate(
        observations,
        product=product,
        inventory=inventory,
        lookback=2,
    )
    second = calculate(
        observations,
        product=product,
        inventory=inventory,
        lookback=2,
    )

    assert product == make_product()
    assert inventory == make_inventory()
    assert observations == original_observations
    assert observations[0].demand_date == date(2026, 7, 2)
    assert first == second
