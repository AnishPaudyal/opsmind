"""Read-only versioned deterministic stockout-exposure endpoint."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from opsmind.api.dependencies import (
    AUTHENTICATION_RESPONSES,
    BusinessReadPrincipal,
    get_product_inventory_repository,
)
from opsmind.domain.errors import (
    InsufficientDemandHistoryError,
    InventoryNotFoundError,
    ProductNotFoundError,
)
from opsmind.domain.stockout import StockoutExposure, calculate_stockout_exposure
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.schemas.stockout import StockoutExposureResponse

router = APIRouter(
    prefix="/products/{product_id}/stockout-exposure",
    tags=["stockout exposure"],
)

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
AsOfDateQuery = Annotated[
    date | None,
    Query(description="Inclusive demand cutoff; defaults to latest demand date."),
]


def _stockout_response(exposure: StockoutExposure) -> StockoutExposureResponse:
    return StockoutExposureResponse(
        product_id=exposure.product_id,
        forecast_method=exposure.forecast_method,
        as_of_date=exposure.as_of_date,
        lookback_observations_requested=(exposure.lookback_observations_requested),
        observations_used=exposure.observations_used,
        training_start_date=exposure.training_start_date,
        training_end_date=exposure.training_end_date,
        average_daily_demand=float(exposure.average_daily_demand),
        lead_time_days=exposure.lead_time_days,
        on_hand_quantity=exposure.on_hand_quantity,
        allocated_quantity=exposure.allocated_quantity,
        available_inventory=exposure.available_inventory,
        forecasted_lead_time_demand=float(exposure.forecasted_lead_time_demand),
        projected_inventory_balance=float(exposure.projected_inventory_balance),
        projected_shortage_quantity=float(exposure.projected_shortage_quantity),
        status=exposure.status,
    )


@router.get(
    "",
    response_model=StockoutExposureResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate deterministic stockout exposure",
    responses={
        **AUTHENTICATION_RESPONSES,
        status.HTTP_404_NOT_FOUND: {
            "description": "Product or inventory position not found."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid parameters or insufficient demand history."
        },
    },
)
def get_stockout_exposure(
    product_id: UUID,
    repository: RepositoryDependency,
    _principal: BusinessReadPrincipal,
    lookback_observations: LookbackQuery = 7,
    as_of_date: AsOfDateQuery = None,
) -> StockoutExposureResponse:
    """Calculate lead-time inventory exposure without mutating state."""
    try:
        product = repository.get_product(product_id)
        inventory = repository.get_inventory(product_id)
        observations = repository.list_demand_observations(product_id)
        exposure = calculate_stockout_exposure(
            product_id=product_id,
            product=product,
            inventory=inventory,
            observations=observations,
            lookback_observations=lookback_observations,
            as_of_date=as_of_date,
        )
    except ProductNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{error.product_id}' was not found.",
        ) from error
    except InventoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory for product '{error.product_id}' was not found.",
        ) from error
    except (InsufficientDemandHistoryError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return _stockout_response(exposure)
