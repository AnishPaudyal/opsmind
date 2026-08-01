"""Read-only versioned deterministic reorder-recommendation endpoint."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from opsmind.api.dependencies import get_product_inventory_repository
from opsmind.domain.errors import (
    InsufficientDemandHistoryError,
    InventoryNotFoundError,
    ProductNotFoundError,
)
from opsmind.domain.reorder import (
    ReorderRecommendation,
    calculate_reorder_recommendation,
)
from opsmind.domain.stockout import calculate_stockout_exposure
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.schemas.reorder import ReorderRecommendationResponse

router = APIRouter(
    prefix="/products/{product_id}/reorder-recommendation",
    tags=["reorder recommendation"],
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


def _reorder_response(
    recommendation: ReorderRecommendation,
) -> ReorderRecommendationResponse:
    return ReorderRecommendationResponse(
        product_id=recommendation.product_id,
        unit_of_measure=recommendation.unit_of_measure,
        recommendation_policy=recommendation.recommendation_policy,
        recommendation_status=recommendation.recommendation_status,
        forecast_method=recommendation.forecast_method,
        as_of_date=recommendation.as_of_date,
        lookback_observations_requested=(
            recommendation.lookback_observations_requested
        ),
        observations_used=recommendation.observations_used,
        training_start_date=recommendation.training_start_date,
        training_end_date=recommendation.training_end_date,
        average_daily_demand=float(recommendation.average_daily_demand),
        lead_time_days=recommendation.lead_time_days,
        on_hand_quantity=recommendation.on_hand_quantity,
        allocated_quantity=recommendation.allocated_quantity,
        available_inventory=recommendation.available_inventory,
        forecasted_lead_time_demand=float(recommendation.forecasted_lead_time_demand),
        projected_inventory_balance=float(recommendation.projected_inventory_balance),
        projected_shortage_quantity=float(recommendation.projected_shortage_quantity),
        recommended_reorder_quantity=(recommendation.recommended_reorder_quantity),
    )


@router.get(
    "",
    response_model=ReorderRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate a deterministic reorder recommendation",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Product or inventory position not found."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid parameters or insufficient demand history."
        },
    },
)
def get_reorder_recommendation(
    product_id: UUID,
    repository: RepositoryDependency,
    lookback_observations: LookbackQuery = 7,
    as_of_date: AsOfDateQuery = None,
) -> ReorderRecommendationResponse:
    """Propose whole units from normalized shortage without mutating state."""
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
        recommendation = calculate_reorder_recommendation(
            exposure=exposure,
            unit_of_measure=product.unit_of_measure,
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
    return _reorder_response(recommendation)
