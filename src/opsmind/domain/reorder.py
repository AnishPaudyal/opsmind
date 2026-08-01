"""Pure deterministic reorder-recommendation policy."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, Decimal
from enum import StrEnum
from uuid import UUID

from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.stockout import StockoutExposure, StockoutExposureStatus


class ReorderRecommendationPolicy(StrEnum):
    """Supported explainable reorder policies."""

    PROJECTED_SHORTAGE_CEILING = "projected_shortage_ceiling"


class ReorderRecommendationStatus(StrEnum):
    """Deterministic proposal outcomes."""

    NO_REORDER_NEEDED = "no_reorder_needed"
    REORDER_RECOMMENDED = "reorder_recommended"


@dataclass(frozen=True, slots=True)
class ReorderRecommendation:
    """One whole-unit proposal with its complete exposure context."""

    product_id: UUID
    unit_of_measure: str
    recommendation_policy: ReorderRecommendationPolicy
    recommendation_status: ReorderRecommendationStatus
    forecast_method: ForecastMethod
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
    recommended_reorder_quantity: int


def calculate_reorder_recommendation(
    *,
    exposure: StockoutExposure,
    unit_of_measure: str,
) -> ReorderRecommendation:
    """Apply whole-unit ceiling to the exposure's normalized public shortage."""
    if not unit_of_measure.strip():
        raise ValueError("unit_of_measure must not be empty")

    public_shortage = exposure.projected_shortage_quantity
    if public_shortage < Decimal("0.00"):
        raise ValueError("projected_shortage_quantity must not be negative")
    if (
        exposure.status is StockoutExposureStatus.SUFFICIENT
        and public_shortage != Decimal("0.00")
    ):
        raise ValueError("sufficient exposure must have zero projected shortage")
    if (
        exposure.status is StockoutExposureStatus.SHORTAGE_PROJECTED
        and public_shortage <= Decimal("0.00")
    ):
        raise ValueError(
            "shortage_projected exposure must have positive projected shortage"
        )

    recommended_quantity = int(
        public_shortage.to_integral_value(rounding=ROUND_CEILING)
    )
    recommendation_status = (
        ReorderRecommendationStatus.NO_REORDER_NEEDED
        if recommended_quantity == 0
        else ReorderRecommendationStatus.REORDER_RECOMMENDED
    )

    return ReorderRecommendation(
        product_id=exposure.product_id,
        unit_of_measure=unit_of_measure,
        recommendation_policy=(ReorderRecommendationPolicy.PROJECTED_SHORTAGE_CEILING),
        recommendation_status=recommendation_status,
        forecast_method=exposure.forecast_method,
        as_of_date=exposure.as_of_date,
        lookback_observations_requested=(exposure.lookback_observations_requested),
        observations_used=exposure.observations_used,
        training_start_date=exposure.training_start_date,
        training_end_date=exposure.training_end_date,
        average_daily_demand=exposure.average_daily_demand,
        lead_time_days=exposure.lead_time_days,
        on_hand_quantity=exposure.on_hand_quantity,
        allocated_quantity=exposure.allocated_quantity,
        available_inventory=exposure.available_inventory,
        forecasted_lead_time_demand=exposure.forecasted_lead_time_demand,
        projected_inventory_balance=exposure.projected_inventory_balance,
        projected_shortage_quantity=public_shortage,
        recommended_reorder_quantity=recommended_quantity,
    )
