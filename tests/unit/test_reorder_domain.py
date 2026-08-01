"""Tests for the pure deterministic reorder-recommendation policy."""

from dataclasses import FrozenInstanceError
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from opsmind.domain.demand import DemandObservation
from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
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

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")


def make_exposure(
    shortage: Decimal = Decimal("0.00"),
    *,
    status: StockoutExposureStatus | None = None,
    balance: Decimal | None = None,
    lead_time_days: int = 5,
    on_hand_quantity: int = 60,
    allocated_quantity: int = 10,
) -> StockoutExposure:
    """Create one immutable public exposure for policy-focused tests."""
    resolved_status = status or (
        StockoutExposureStatus.SUFFICIENT
        if shortage == Decimal("0.00")
        else StockoutExposureStatus.SHORTAGE_PROJECTED
    )
    resolved_balance = (
        balance
        if balance is not None
        else (Decimal("1.25") if shortage == 0 else -shortage)
    )
    return StockoutExposure(
        product_id=PRODUCT_ID,
        forecast_method=ForecastMethod.SIMPLE_MEAN,
        as_of_date=date(2026, 7, 4),
        lookback_observations_requested=4,
        observations_used=4,
        training_start_date=date(2026, 7, 1),
        training_end_date=date(2026, 7, 4),
        average_daily_demand=Decimal("9.75"),
        lead_time_days=lead_time_days,
        on_hand_quantity=on_hand_quantity,
        allocated_quantity=allocated_quantity,
        available_inventory=on_hand_quantity - allocated_quantity,
        forecasted_lead_time_demand=Decimal("48.75"),
        projected_inventory_balance=resolved_balance,
        projected_shortage_quantity=shortage,
        status=resolved_status,
    )


def recommend(
    exposure: StockoutExposure,
    unit_of_measure: str = "units",
) -> ReorderRecommendation:
    """Apply the production policy with deterministic defaults."""
    return calculate_reorder_recommendation(
        exposure=exposure,
        unit_of_measure=unit_of_measure,
    )


def test_sufficient_positive_balance_returns_complete_zero_proposal() -> None:
    exposure = make_exposure()

    result = recommend(exposure)

    assert result.product_id == PRODUCT_ID
    assert result.unit_of_measure == "units"
    assert (
        result.recommendation_policy
        is ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING
    )
    assert result.recommendation_status is ReorderRecommendationStatus.NO_REORDER_NEEDED
    assert result.recommended_reorder_quantity == 0
    assert result.projected_inventory_balance == Decimal("1.25")
    assert result.projected_shortage_quantity == Decimal("0.00")


def test_exact_zero_and_normalized_rounded_zero_recommend_nothing() -> None:
    exact_zero = recommend(make_exposure(balance=Decimal("0.00")))
    normalized_zero = recommend(
        make_exposure(
            balance=Decimal("0.00"),
            shortage=Decimal("0.00"),
        )
    )

    assert exact_zero.recommended_reorder_quantity == 0
    assert normalized_zero.recommended_reorder_quantity == 0
    assert exact_zero.recommendation_status.value == "no_reorder_needed"
    assert normalized_zero.recommendation_status.value == "no_reorder_needed"


@pytest.mark.parametrize(
    ("shortage", "expected_quantity"),
    [
        (Decimal("0.01"), 1),
        (Decimal("1.00"), 1),
        (Decimal("1.01"), 2),
        (Decimal("18.00"), 18),
        (Decimal("18.75"), 19),
    ],
)
def test_decimal_ceiling_boundaries(
    shortage: Decimal,
    expected_quantity: int,
) -> None:
    result = recommend(make_exposure(shortage))

    assert result.recommended_reorder_quantity == expected_quantity
    assert (
        result.recommendation_status is ReorderRecommendationStatus.REORDER_RECOMMENDED
    )


def test_decimal_ceiling_does_not_convert_to_binary_float() -> None:
    shortage = Decimal("9007199254740992.01")

    result = recommend(make_exposure(shortage))

    assert result.recommended_reorder_quantity == 9007199254740993


def test_public_shortage_is_policy_input_without_balance_recalculation() -> None:
    exposure = make_exposure(
        Decimal("0.01"),
        balance=Decimal("-999.99"),
    )

    result = recommend(exposure)

    assert result.projected_shortage_quantity == Decimal("0.01")
    assert result.recommended_reorder_quantity == 1


@pytest.mark.parametrize(
    ("exposure", "expected_quantity"),
    [
        (
            make_exposure(Decimal("20.00"), on_hand_quantity=20, allocated_quantity=30),
            20,
        ),
        (
            make_exposure(
                Decimal("10.00"),
                lead_time_days=0,
                on_hand_quantity=0,
                allocated_quantity=10,
            ),
            10,
        ),
        (make_exposure(lead_time_days=0, on_hand_quantity=10, allocated_quantity=0), 0),
        (make_exposure(lead_time_days=500), 0),
    ],
)
def test_inventory_and_lead_time_context_is_preserved(
    exposure: StockoutExposure,
    expected_quantity: int,
) -> None:
    result = recommend(exposure)

    assert result.available_inventory == exposure.available_inventory
    assert result.lead_time_days == exposure.lead_time_days
    assert result.recommended_reorder_quantity == expected_quantity


def test_all_exposure_fields_and_unit_are_copied_exactly() -> None:
    exposure = make_exposure(Decimal("18.75"), on_hand_quantity=40)

    result = recommend(exposure, "cases")

    assert result.unit_of_measure == "cases"
    assert result.forecast_method is exposure.forecast_method
    assert result.as_of_date == exposure.as_of_date
    assert (
        result.lookback_observations_requested
        == exposure.lookback_observations_requested
    )
    assert result.observations_used == exposure.observations_used
    assert result.training_start_date == exposure.training_start_date
    assert result.training_end_date == exposure.training_end_date
    assert result.average_daily_demand == exposure.average_daily_demand
    assert result.lead_time_days == exposure.lead_time_days
    assert result.on_hand_quantity == exposure.on_hand_quantity
    assert result.allocated_quantity == exposure.allocated_quantity
    assert result.available_inventory == exposure.available_inventory
    assert result.forecasted_lead_time_demand == exposure.forecasted_lead_time_demand
    assert result.projected_inventory_balance == exposure.projected_inventory_balance
    assert result.projected_shortage_quantity == exposure.projected_shortage_quantity


def test_inputs_remain_unchanged_and_identical_calls_are_equal() -> None:
    exposure = make_exposure(Decimal("18.75"), on_hand_quantity=40)
    unit_of_measure = "units"

    first = recommend(exposure, unit_of_measure)
    second = recommend(exposure, unit_of_measure)

    assert exposure == make_exposure(Decimal("18.75"), on_hand_quantity=40)
    assert unit_of_measure == "units"
    assert first == second
    with pytest.raises(FrozenInstanceError):
        first.recommended_reorder_quantity = 20  # type: ignore[misc]


def test_recorded_zero_and_all_zero_history_compose_through_stockout() -> None:
    product = Product(
        id=PRODUCT_ID,
        sku="SENSOR-001",
        name="Sensor",
        unit_of_measure="units",
        lead_time_days=30,
        is_active=True,
    )
    inventory = InventoryPosition(PRODUCT_ID, 0, 0)
    observations = (
        DemandObservation(PRODUCT_ID, date(2026, 7, 1), 0),
        DemandObservation(PRODUCT_ID, date(2026, 7, 10), 0),
    )
    exposure = calculate_stockout_exposure(
        product_id=PRODUCT_ID,
        product=product,
        inventory=inventory,
        observations=observations,
        lookback_observations=7,
    )

    result = recommend(exposure, product.unit_of_measure)

    assert result.observations_used == 2
    assert result.average_daily_demand == Decimal("0.00")
    assert result.projected_shortage_quantity == Decimal("0.00")
    assert result.recommended_reorder_quantity == 0


def test_negative_zero_normalization_composes_to_zero_recommendation() -> None:
    product = Product(
        id=PRODUCT_ID,
        sku="SENSOR-001",
        name="Sensor",
        unit_of_measure="units",
        lead_time_days=1,
        is_active=True,
    )
    inventory = InventoryPosition(PRODUCT_ID, 0, 0)
    first_date = date(2025, 1, 1)
    observations = tuple(
        DemandObservation(
            PRODUCT_ID,
            first_date + timedelta(days=index),
            1 if index == 0 else 0,
        )
        for index in range(365)
    )
    exposure = calculate_stockout_exposure(
        product_id=PRODUCT_ID,
        product=product,
        inventory=inventory,
        observations=observations,
        lookback_observations=365,
    )

    result = recommend(exposure)

    assert exposure.projected_shortage_quantity == Decimal("0.00")
    assert result.recommended_reorder_quantity == 0
    assert result.recommendation_status.value == "no_reorder_needed"


def test_negative_shortage_fails_safely() -> None:
    with pytest.raises(
        ValueError,
        match=r"^projected_shortage_quantity must not be negative$",
    ):
        recommend(make_exposure(Decimal("-0.01")))


def test_sufficient_exposure_with_positive_shortage_fails_safely() -> None:
    with pytest.raises(
        ValueError,
        match=r"^sufficient exposure must have zero projected shortage$",
    ):
        recommend(
            make_exposure(
                Decimal("0.01"),
                status=StockoutExposureStatus.SUFFICIENT,
            )
        )


def test_shortage_exposure_with_zero_shortage_fails_safely() -> None:
    with pytest.raises(
        ValueError,
        match=(r"^shortage_projected exposure must have positive projected shortage$"),
    ):
        recommend(
            make_exposure(
                Decimal("0.00"),
                status=StockoutExposureStatus.SHORTAGE_PROJECTED,
            )
        )


@pytest.mark.parametrize("unit_of_measure", ["", " ", "\t"])
def test_empty_unit_of_measure_fails_safely(unit_of_measure: str) -> None:
    with pytest.raises(ValueError, match=r"^unit_of_measure must not be empty$"):
        recommend(make_exposure(), unit_of_measure)
