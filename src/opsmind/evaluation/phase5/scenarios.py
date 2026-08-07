"""Deterministic synthetic scenarios for the governed Phase 5 evaluation."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from opsmind.domain.demand import DemandObservation
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
from opsmind.domain.reorder import (
    ReorderRecommendationPolicy,
    ReorderRecommendationStatus,
)
from opsmind.domain.stockout import StockoutExposureStatus

DATASET_VERSION = "phase5-synthetic-v1"


@dataclass(frozen=True, slots=True)
class ExpectedOutcome:
    """Expected public stockout and reorder outcome for one governed scenario."""

    as_of_date: date
    lookback_observations_requested: int
    observations_used: int
    training_start_date: date
    training_end_date: date
    average_daily_demand: Decimal
    lead_time_days: int
    on_hand_quantity: int
    allocated_quantity: int
    available_inventory: int
    forecasted_lead_time_demand: Decimal
    projected_inventory_balance: Decimal
    projected_shortage_quantity: Decimal
    exposure_status: StockoutExposureStatus
    recommendation_policy: ReorderRecommendationPolicy
    recommendation_status: ReorderRecommendationStatus
    recommended_reorder_quantity: int


@dataclass(frozen=True, slots=True)
class Phase5Scenario:
    """One deterministic scenario and its independently specified expectation."""

    scenario_name: str
    product_id: UUID
    product: Product
    inventory: InventoryPosition
    observations: tuple[DemandObservation, ...]
    lookback_observations: int
    as_of_date: date
    expected: ExpectedOutcome


def _product_id(index: int) -> UUID:
    return UUID(f"00000000-0000-0000-0000-{5000 + index:012d}")


def _product(index: int, *, lead_time_days: int) -> Product:
    product_id = _product_id(index)
    return Product(
        id=product_id,
        sku=f"PHASE5-{index:02d}",
        name=f"Phase 5 Scenario {index:02d}",
        unit_of_measure="units",
        lead_time_days=lead_time_days,
        is_active=True,
    )


def _observations(
    product_id: UUID,
    items: tuple[tuple[date, int], ...],
) -> tuple[DemandObservation, ...]:
    return tuple(
        DemandObservation(product_id, demand_date, quantity)
        for demand_date, quantity in items
    )


def _expected(
    *,
    as_of_date: date,
    lookback: int,
    used: int,
    training_start: date,
    training_end: date,
    average: str,
    lead_time_days: int,
    on_hand: int,
    allocated: int,
    available: int,
    lead_time_demand: str,
    balance: str,
    shortage: str,
    exposure_status: StockoutExposureStatus,
    recommendation_status: ReorderRecommendationStatus,
    reorder_quantity: int,
) -> ExpectedOutcome:
    return ExpectedOutcome(
        as_of_date=as_of_date,
        lookback_observations_requested=lookback,
        observations_used=used,
        training_start_date=training_start,
        training_end_date=training_end,
        average_daily_demand=Decimal(average),
        lead_time_days=lead_time_days,
        on_hand_quantity=on_hand,
        allocated_quantity=allocated,
        available_inventory=available,
        forecasted_lead_time_demand=Decimal(lead_time_demand),
        projected_inventory_balance=Decimal(balance),
        projected_shortage_quantity=Decimal(shortage),
        exposure_status=exposure_status,
        recommendation_policy=ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING,
        recommendation_status=recommendation_status,
        recommended_reorder_quantity=reorder_quantity,
    )


def _scenario(
    *,
    index: int,
    scenario_name: str,
    lead_time_days: int,
    on_hand_quantity: int,
    allocated_quantity: int,
    demand: tuple[tuple[date, int], ...],
    lookback_observations: int,
    as_of_date: date,
    expected: ExpectedOutcome,
) -> Phase5Scenario:
    product = _product(index, lead_time_days=lead_time_days)
    return Phase5Scenario(
        scenario_name=scenario_name,
        product_id=product.id,
        product=product,
        inventory=InventoryPosition(
            product_id=product.id,
            on_hand_quantity=on_hand_quantity,
            allocated_quantity=allocated_quantity,
        ),
        observations=_observations(product.id, demand),
        lookback_observations=lookback_observations,
        as_of_date=as_of_date,
        expected=expected,
    )


def build_phase5_scenarios() -> tuple[Phase5Scenario, ...]:
    """Return the complete deterministic Phase 5 scenario-conformance dataset."""

    jul1 = date(2026, 7, 1)
    jul2 = date(2026, 7, 2)
    jul3 = date(2026, 7, 3)
    jul4 = date(2026, 7, 4)
    jul10 = date(2026, 7, 10)
    jul20 = date(2026, 7, 20)
    standard_tens = ((jul1, 10), (jul2, 10), (jul3, 10), (jul4, 10))

    small_start = date(2026, 1, 1)
    small_demand = tuple(
        (small_start + timedelta(days=offset), 1 if offset == 99 else 0)
        for offset in range(100)
    )
    small_end = small_start + timedelta(days=99)

    scenarios = (
        _scenario(
            index=1,
            scenario_name="sufficient_buffer",
            lead_time_days=5,
            on_hand_quantity=70,
            allocated_quantity=10,
            demand=standard_tens,
            lookback_observations=4,
            as_of_date=jul4,
            expected=_expected(
                as_of_date=jul4,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul4,
                average="10.00",
                lead_time_days=5,
                on_hand=70,
                allocated=10,
                available=60,
                lead_time_demand="50.00",
                balance="10.00",
                shortage="0.00",
                exposure_status=StockoutExposureStatus.SUFFICIENT,
                recommendation_status=ReorderRecommendationStatus.NO_REORDER_NEEDED,
                reorder_quantity=0,
            ),
        ),
        _scenario(
            index=2,
            scenario_name="exact_coverage_boundary",
            lead_time_days=5,
            on_hand_quantity=60,
            allocated_quantity=10,
            demand=standard_tens,
            lookback_observations=4,
            as_of_date=jul4,
            expected=_expected(
                as_of_date=jul4,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul4,
                average="10.00",
                lead_time_days=5,
                on_hand=60,
                allocated=10,
                available=50,
                lead_time_demand="50.00",
                balance="0.00",
                shortage="0.00",
                exposure_status=StockoutExposureStatus.SUFFICIENT,
                recommendation_status=ReorderRecommendationStatus.NO_REORDER_NEEDED,
                reorder_quantity=0,
            ),
        ),
        _scenario(
            index=3,
            scenario_name="fractional_shortage",
            lead_time_days=5,
            on_hand_quantity=40,
            allocated_quantity=10,
            demand=((jul1, 12), (jul2, 18), (jul3, 9), (jul4, 0)),
            lookback_observations=4,
            as_of_date=jul4,
            expected=_expected(
                as_of_date=jul4,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul4,
                average="9.75",
                lead_time_days=5,
                on_hand=40,
                allocated=10,
                available=30,
                lead_time_demand="48.75",
                balance="-18.75",
                shortage="18.75",
                exposure_status=StockoutExposureStatus.SHORTAGE_PROJECTED,
                recommendation_status=ReorderRecommendationStatus.REORDER_RECOMMENDED,
                reorder_quantity=19,
            ),
        ),
        _scenario(
            index=4,
            scenario_name="whole_unit_shortage",
            lead_time_days=5,
            on_hand_quantity=40,
            allocated_quantity=10,
            demand=standard_tens,
            lookback_observations=4,
            as_of_date=jul4,
            expected=_expected(
                as_of_date=jul4,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul4,
                average="10.00",
                lead_time_days=5,
                on_hand=40,
                allocated=10,
                available=30,
                lead_time_demand="50.00",
                balance="-20.00",
                shortage="20.00",
                exposure_status=StockoutExposureStatus.SHORTAGE_PROJECTED,
                recommendation_status=ReorderRecommendationStatus.REORDER_RECOMMENDED,
                reorder_quantity=20,
            ),
        ),
        _scenario(
            index=5,
            scenario_name="small_fractional_shortage",
            lead_time_days=1,
            on_hand_quantity=0,
            allocated_quantity=0,
            demand=small_demand,
            lookback_observations=100,
            as_of_date=small_end,
            expected=_expected(
                as_of_date=small_end,
                lookback=100,
                used=100,
                training_start=small_start,
                training_end=small_end,
                average="0.01",
                lead_time_days=1,
                on_hand=0,
                allocated=0,
                available=0,
                lead_time_demand="0.01",
                balance="-0.01",
                shortage="0.01",
                exposure_status=StockoutExposureStatus.SHORTAGE_PROJECTED,
                recommendation_status=ReorderRecommendationStatus.REORDER_RECOMMENDED,
                reorder_quantity=1,
            ),
        ),
        _scenario(
            index=6,
            scenario_name="negative_available_inventory",
            lead_time_days=5,
            on_hand_quantity=5,
            allocated_quantity=10,
            demand=((jul1, 0), (jul2, 0), (jul3, 0), (jul4, 0)),
            lookback_observations=4,
            as_of_date=jul4,
            expected=_expected(
                as_of_date=jul4,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul4,
                average="0.00",
                lead_time_days=5,
                on_hand=5,
                allocated=10,
                available=-5,
                lead_time_demand="0.00",
                balance="-5.00",
                shortage="5.00",
                exposure_status=StockoutExposureStatus.SHORTAGE_PROJECTED,
                recommendation_status=ReorderRecommendationStatus.REORDER_RECOMMENDED,
                reorder_quantity=5,
            ),
        ),
        _scenario(
            index=7,
            scenario_name="zero_lead_time",
            lead_time_days=0,
            on_hand_quantity=0,
            allocated_quantity=0,
            demand=standard_tens,
            lookback_observations=4,
            as_of_date=jul4,
            expected=_expected(
                as_of_date=jul4,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul4,
                average="10.00",
                lead_time_days=0,
                on_hand=0,
                allocated=0,
                available=0,
                lead_time_demand="0.00",
                balance="0.00",
                shortage="0.00",
                exposure_status=StockoutExposureStatus.SUFFICIENT,
                recommendation_status=ReorderRecommendationStatus.NO_REORDER_NEEDED,
                reorder_quantity=0,
            ),
        ),
        _scenario(
            index=8,
            scenario_name="recorded_zero_demand",
            lead_time_days=30,
            on_hand_quantity=0,
            allocated_quantity=0,
            demand=((jul1, 0), (jul3, 0), (jul10, 0), (jul20, 0)),
            lookback_observations=4,
            as_of_date=jul20,
            expected=_expected(
                as_of_date=jul20,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul20,
                average="0.00",
                lead_time_days=30,
                on_hand=0,
                allocated=0,
                available=0,
                lead_time_demand="0.00",
                balance="0.00",
                shortage="0.00",
                exposure_status=StockoutExposureStatus.SUFFICIENT,
                recommendation_status=ReorderRecommendationStatus.NO_REORDER_NEEDED,
                reorder_quantity=0,
            ),
        ),
        _scenario(
            index=9,
            scenario_name="cutoff_excludes_future_observation",
            lead_time_days=5,
            on_hand_quantity=50,
            allocated_quantity=0,
            demand=(*standard_tens, (jul10, 100)),
            lookback_observations=4,
            as_of_date=jul4,
            expected=_expected(
                as_of_date=jul4,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul4,
                average="10.00",
                lead_time_days=5,
                on_hand=50,
                allocated=0,
                available=50,
                lead_time_demand="50.00",
                balance="0.00",
                shortage="0.00",
                exposure_status=StockoutExposureStatus.SUFFICIENT,
                recommendation_status=ReorderRecommendationStatus.NO_REORDER_NEEDED,
                reorder_quantity=0,
            ),
        ),
        _scenario(
            index=10,
            scenario_name="observation_count_lookback_missing_dates",
            lead_time_days=2,
            on_hand_quantity=35,
            allocated_quantity=0,
            demand=((jul1, 5), (jul10, 15), (jul20, 25)),
            lookback_observations=2,
            as_of_date=jul20,
            expected=_expected(
                as_of_date=jul20,
                lookback=2,
                used=2,
                training_start=jul10,
                training_end=jul20,
                average="20.00",
                lead_time_days=2,
                on_hand=35,
                allocated=0,
                available=35,
                lead_time_demand="40.00",
                balance="-5.00",
                shortage="5.00",
                exposure_status=StockoutExposureStatus.SHORTAGE_PROJECTED,
                recommendation_status=ReorderRecommendationStatus.REORDER_RECOMMENDED,
                reorder_quantity=5,
            ),
        ),
        _scenario(
            index=11,
            scenario_name="large_lead_time_shortage",
            lead_time_days=30,
            on_hand_quantity=0,
            allocated_quantity=0,
            demand=standard_tens,
            lookback_observations=4,
            as_of_date=jul4,
            expected=_expected(
                as_of_date=jul4,
                lookback=4,
                used=4,
                training_start=jul1,
                training_end=jul4,
                average="10.00",
                lead_time_days=30,
                on_hand=0,
                allocated=0,
                available=0,
                lead_time_demand="300.00",
                balance="-300.00",
                shortage="300.00",
                exposure_status=StockoutExposureStatus.SHORTAGE_PROJECTED,
                recommendation_status=ReorderRecommendationStatus.REORDER_RECOMMENDED,
                reorder_quantity=300,
            ),
        ),
    )
    return tuple(sorted(scenarios, key=lambda scenario: scenario.scenario_name))
