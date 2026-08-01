"""Public deterministic stockout-exposure response schema."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from opsmind.domain.forecast import ForecastMethod
from opsmind.domain.stockout import StockoutExposureStatus


class StockoutExposureResponse(BaseModel):
    """Explanatory lead-time inventory coverage for one product."""

    product_id: UUID = Field(description="Product whose exposure was calculated.")
    forecast_method: ForecastMethod = Field(
        description="Deterministic demand baseline used.",
        examples=[ForecastMethod.SIMPLE_MEAN],
    )
    as_of_date: date = Field(
        description="Inclusive effective cutoff for eligible demand.",
        examples=["2026-07-04"],
    )
    lookback_observations_requested: int = Field(
        description="Requested count of recent eligible observations.",
        examples=[4],
    )
    observations_used: int = Field(
        description="Actual count of demand observations selected.",
        examples=[4],
    )
    training_start_date: date = Field(
        description="Earliest selected demand date.",
        examples=["2026-07-01"],
    )
    training_end_date: date = Field(
        description="Latest selected demand date.",
        examples=["2026-07-04"],
    )
    average_daily_demand: float = Field(
        description="Selected arithmetic mean rounded to two decimals.",
        examples=[9.75],
    )
    lead_time_days: int = Field(
        description="Product replenishment lead time used as the horizon.",
        examples=[5],
    )
    on_hand_quantity: int = Field(
        description="Current physical inventory quantity.",
        examples=[60],
    )
    allocated_quantity: int = Field(
        description="Current committed inventory quantity.",
        examples=[10],
    )
    available_inventory: int = Field(
        description="On-hand quantity minus allocated quantity.",
        examples=[50],
    )
    forecasted_lead_time_demand: float = Field(
        description="Exact mean projected across product lead time.",
        examples=[48.75],
    )
    projected_inventory_balance: float = Field(
        description="Available inventory minus lead-time demand.",
        examples=[1.25],
    )
    projected_shortage_quantity: float = Field(
        description="Non-negative shortage derived from the public balance.",
        examples=[0.0],
    )
    status: StockoutExposureStatus = Field(
        description="Deterministic sufficiency status, not a probability.",
        examples=[StockoutExposureStatus.SUFFICIENT],
    )
