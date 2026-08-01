"""Public baseline-demand forecast response schema."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field

from opsmind.domain.forecast import ForecastMethod


class ForecastResponse(BaseModel):
    """Transparent metadata and numeric output for one baseline forecast."""

    product_id: UUID = Field(description="Product whose demand was forecast.")
    method: ForecastMethod = Field(
        description="Deterministic forecast method used.",
        examples=[ForecastMethod.SIMPLE_MEAN],
    )
    as_of_date: date = Field(
        description="Inclusive effective cutoff for eligible demand.",
        examples=["2026-07-04"],
    )
    lookback_observations_requested: int = Field(
        description="Requested count of recent eligible observations.",
        examples=[7],
    )
    observations_used: int = Field(
        description="Actual count of observations included.",
        examples=[4],
    )
    training_start_date: date = Field(
        description="Earliest selected observation date.",
        examples=["2026-07-01"],
    )
    training_end_date: date = Field(
        description="Latest selected observation date.",
        examples=["2026-07-04"],
    )
    average_daily_demand: float = Field(
        description="Arithmetic mean rounded independently to two decimals.",
        examples=[9.75],
    )
    horizon_days: int = Field(
        description="Number of forecast days.",
        examples=[7],
    )
    forecast_quantity: float = Field(
        description="Exact mean times horizon, rounded to two decimals.",
        examples=[68.25],
    )
