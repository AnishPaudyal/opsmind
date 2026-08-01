"""Pure deterministic stockout-exposure calculation."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from opsmind.domain.demand import DemandObservation
from opsmind.domain.forecast import (
    ForecastMethod,
    calculate_simple_mean_statistics,
    quantize_two_decimal_places,
)
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product


class StockoutExposureStatus(StrEnum):
    """Deterministic inventory-coverage outcomes."""

    SUFFICIENT = "sufficient"
    SHORTAGE_PROJECTED = "shortage_projected"


@dataclass(frozen=True, slots=True)
class StockoutExposure:
    """Explain current inventory coverage across product lead time."""

    product_id: UUID
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
    status: StockoutExposureStatus


def calculate_stockout_exposure(
    *,
    product_id: UUID,
    product: Product,
    inventory: InventoryPosition,
    observations: tuple[DemandObservation, ...],
    lookback_observations: int,
    as_of_date: date | None = None,
) -> StockoutExposure:
    """Calculate read-only lead-time exposure from exact demand statistics."""
    if product.id != product_id:
        raise ValueError("product id must match requested product_id")
    if inventory.product_id != product_id:
        raise ValueError("inventory product_id must match requested product_id")

    statistics = calculate_simple_mean_statistics(
        product_id=product_id,
        observations=observations,
        lookback_observations=lookback_observations,
        as_of_date=as_of_date,
    )
    available_inventory = inventory.available_quantity
    exact_lead_time_demand = statistics.exact_average_daily_demand * Decimal(
        product.lead_time_days
    )
    exact_projected_balance = Decimal(available_inventory) - exact_lead_time_demand

    public_lead_time_demand = quantize_two_decimal_places(exact_lead_time_demand)
    public_balance = quantize_two_decimal_places(exact_projected_balance)
    public_shortage = quantize_two_decimal_places(max(-public_balance, Decimal("0.00")))
    exposure_status = (
        StockoutExposureStatus.SUFFICIENT
        if public_balance >= Decimal("0.00")
        else StockoutExposureStatus.SHORTAGE_PROJECTED
    )

    return StockoutExposure(
        product_id=product_id,
        forecast_method=ForecastMethod.SIMPLE_MEAN,
        as_of_date=statistics.as_of_date,
        lookback_observations_requested=(statistics.lookback_observations_requested),
        observations_used=statistics.observations_used,
        training_start_date=statistics.training_start_date,
        training_end_date=statistics.training_end_date,
        average_daily_demand=quantize_two_decimal_places(
            statistics.exact_average_daily_demand
        ),
        lead_time_days=product.lead_time_days,
        on_hand_quantity=inventory.on_hand_quantity,
        allocated_quantity=inventory.allocated_quantity,
        available_inventory=available_inventory,
        forecasted_lead_time_demand=public_lead_time_demand,
        projected_inventory_balance=public_balance,
        projected_shortage_quantity=public_shortage,
        status=exposure_status,
    )
