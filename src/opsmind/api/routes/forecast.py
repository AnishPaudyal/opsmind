"""Read-only versioned baseline-demand forecast endpoint."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from opsmind.api.dependencies import get_product_inventory_repository
from opsmind.domain.errors import (
    InsufficientDemandHistoryError,
    ProductNotFoundError,
)
from opsmind.domain.forecast import BaselineForecast, calculate_simple_mean_forecast
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.schemas.forecast import ForecastResponse

router = APIRouter(prefix="/products/{product_id}/forecast", tags=["forecast"])

RepositoryDependency = Annotated[
    ProductInventoryRepository,
    Depends(get_product_inventory_repository),
]
LookbackQuery = Annotated[
    int,
    Query(
        ge=1,
        le=365,
        description="Number of recent eligible demand observations to use.",
    ),
]
HorizonQuery = Annotated[
    int,
    Query(
        ge=1,
        le=365,
        description="Number of future days covered by the forecast.",
    ),
]
AsOfDateQuery = Annotated[
    date | None,
    Query(description="Inclusive demand cutoff; defaults to latest demand date."),
]


def _forecast_response(forecast: BaselineForecast) -> ForecastResponse:
    return ForecastResponse(
        product_id=forecast.product_id,
        method=forecast.method,
        as_of_date=forecast.as_of_date,
        lookback_observations_requested=forecast.lookback_observations_requested,
        observations_used=forecast.observations_used,
        training_start_date=forecast.training_start_date,
        training_end_date=forecast.training_end_date,
        average_daily_demand=float(forecast.average_daily_demand),
        horizon_days=forecast.horizon_days,
        forecast_quantity=float(forecast.forecast_quantity),
    )


@router.get(
    "",
    response_model=ForecastResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate a baseline demand forecast",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Product not found."},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid parameters or insufficient demand history."
        },
    },
)
def get_baseline_demand_forecast(
    product_id: UUID,
    repository: RepositoryDependency,
    lookback_observations: LookbackQuery = 7,
    horizon_days: HorizonQuery = 7,
    as_of_date: AsOfDateQuery = None,
) -> ForecastResponse:
    """Calculate a deterministic forecast without storing or mutating state."""
    try:
        observations = repository.list_demand_observations(product_id)
        forecast = calculate_simple_mean_forecast(
            product_id=product_id,
            observations=observations,
            lookback_observations=lookback_observations,
            horizon_days=horizon_days,
            as_of_date=as_of_date,
        )
    except ProductNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{error.product_id}' was not found.",
        ) from error
    except InsufficientDemandHistoryError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return _forecast_response(forecast)
