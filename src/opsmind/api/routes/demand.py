"""Versioned demand-history ingestion and retrieval endpoints."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from opsmind.api.dependencies import (
    AUTHENTICATION_RESPONSES,
    BusinessReadPrincipal,
    BusinessWritePrincipal,
    get_product_inventory_repository,
)
from opsmind.domain.demand import DemandObservation
from opsmind.domain.errors import DuplicateDemandDateError, ProductNotFoundError
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.schemas.demand import (
    DemandBatchCreate,
    DemandObservationResponse,
)

router = APIRouter(prefix="/products/{product_id}/demand", tags=["demand"])

RepositoryDependency = Annotated[
    ProductInventoryRepository,
    Depends(get_product_inventory_repository),
]

StartDateQuery = Annotated[
    date | None,
    Query(description="Inclusive first demand date to return."),
]
EndDateQuery = Annotated[
    date | None,
    Query(description="Inclusive last demand date to return."),
]


def _demand_response(observation: DemandObservation) -> DemandObservationResponse:
    return DemandObservationResponse(
        product_id=observation.product_id,
        demand_date=observation.demand_date,
        quantity=observation.quantity,
    )


def _product_not_found(error: ProductNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product '{error.product_id}' was not found.",
    )


@router.post(
    "",
    response_model=list[DemandObservationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add product demand observations",
    responses={
        **AUTHENTICATION_RESPONSES,
        status.HTTP_404_NOT_FOUND: {"description": "Product not found."},
        status.HTTP_409_CONFLICT: {
            "description": "Demand already exists for a submitted date."
        },
    },
)
def add_demand_observations(
    product_id: UUID,
    request: DemandBatchCreate,
    repository: RepositoryDependency,
    _principal: BusinessWritePrincipal,
) -> list[DemandObservationResponse]:
    """Atomically add one batch and return it chronologically."""
    observations = tuple(
        DemandObservation(
            product_id=product_id,
            demand_date=item.demand_date,
            quantity=item.quantity,
        )
        for item in request.observations
    )
    try:
        stored_observations = repository.add_demand_observations(
            product_id,
            observations,
        )
    except ProductNotFoundError as error:
        raise _product_not_found(error) from error
    except DuplicateDemandDateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Demand for product '{error.product_id}' on "
                f"'{error.demand_date.isoformat()}' already exists."
            ),
        ) from error
    return [_demand_response(observation) for observation in stored_observations]


@router.get(
    "",
    response_model=list[DemandObservationResponse],
    status_code=status.HTTP_200_OK,
    summary="List product demand observations",
    responses={
        **AUTHENTICATION_RESPONSES,
        status.HTTP_404_NOT_FOUND: {"description": "Product not found."},
    },
)
def list_demand_observations(
    product_id: UUID,
    repository: RepositoryDependency,
    _principal: BusinessReadPrincipal,
    start_date: StartDateQuery = None,
    end_date: EndDateQuery = None,
) -> list[DemandObservationResponse]:
    """Return chronological demand within optional inclusive bounds."""
    try:
        observations = repository.list_demand_observations(
            product_id,
            start_date=start_date,
            end_date=end_date,
        )
    except ProductNotFoundError as error:
        raise _product_not_found(error) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return [_demand_response(observation) for observation in observations]
