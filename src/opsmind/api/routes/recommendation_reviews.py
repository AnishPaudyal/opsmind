"""Stored recommendation-review creation, retrieval, and decisions."""

from datetime import date
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status

from opsmind.api.dependencies import (
    get_clock,
    get_product_inventory_repository,
    get_recommendation_workflow_repository,
)
from opsmind.core.clock import Clock
from opsmind.domain.errors import (
    DuplicateRecommendationReviewError,
    InsufficientDemandHistoryError,
    InventoryNotFoundError,
    NoActionableReorderRecommendationError,
    ProductNotFoundError,
    RecommendationReviewConflictError,
    RecommendationReviewNotFoundError,
)
from opsmind.domain.recommendation_review import (
    RecommendationDecision,
    ReorderRecommendationReview,
    create_recommendation_review,
)
from opsmind.domain.reorder import (
    ReorderRecommendation,
    calculate_reorder_recommendation,
)
from opsmind.domain.stockout import calculate_stockout_exposure
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.repositories.recommendation_workflow import (
    RecommendationWorkflowRepository,
)
from opsmind.schemas.recommendation_review import (
    ApproveRecommendationRequest,
    RecommendationDecisionResponse,
    RejectRecommendationRequest,
    ReorderRecommendationReviewResponse,
)
from opsmind.schemas.reorder import ReorderRecommendationResponse

router = APIRouter(tags=["reorder recommendation review"])

ProductRepositoryDependency = Annotated[
    ProductInventoryRepository,
    Depends(get_product_inventory_repository),
]
WorkflowRepositoryDependency = Annotated[
    RecommendationWorkflowRepository,
    Depends(get_recommendation_workflow_repository),
]
ClockDependency = Annotated[Clock, Depends(get_clock)]
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


def _recommendation_response(
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


def _decision_response(
    decision: RecommendationDecision,
) -> RecommendationDecisionResponse:
    return RecommendationDecisionResponse(
        decision_id=decision.decision_id,
        decision_type=decision.decision_type,
        decided_by=decision.decided_by,
        decided_at=decision.decided_at,
        approved_quantity=decision.approved_quantity,
        note=decision.note,
    )


def _review_response(
    review: ReorderRecommendationReview,
) -> ReorderRecommendationReviewResponse:
    return ReorderRecommendationReviewResponse(
        recommendation_id=review.recommendation_id,
        recommendation=_recommendation_response(review.recommendation),
        review_status=review.review_status,
        created_at=review.created_at,
        decision=(
            None if review.decision is None else _decision_response(review.decision)
        ),
    )


def _review_not_found(error: RecommendationReviewNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(f"Reorder recommendation '{error.recommendation_id}' was not found."),
    )


@router.post(
    "/products/{product_id}/reorder-recommendations",
    response_model=ReorderRecommendationReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a stored reorder recommendation review",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Product or inventory position not found."
        },
        status.HTTP_409_CONFLICT: {
            "description": "No actionable recommendation is available."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid parameters or insufficient demand history."
        },
    },
)
def create_reorder_recommendation_review(
    product_id: UUID,
    product_repository: ProductRepositoryDependency,
    workflow_repository: WorkflowRepositoryDependency,
    clock: ClockDependency,
    lookback_observations: LookbackQuery = 7,
    as_of_date: AsOfDateQuery = None,
) -> ReorderRecommendationReviewResponse:
    """Calculate and store one immutable actionable recommendation snapshot."""
    try:
        product = product_repository.get_product(product_id)
        inventory = product_repository.get_inventory(product_id)
        observations = product_repository.list_demand_observations(product_id)
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
        review = create_recommendation_review(
            recommendation_id=uuid4(),
            recommendation=recommendation,
            created_at=clock.now(),
        )
        stored_review = workflow_repository.create_review(review)
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
    except NoActionableReorderRecommendationError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except DuplicateRecommendationReviewError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Reorder recommendation '{error.recommendation_id}' already exists."
            ),
        ) from error
    except (InsufficientDemandHistoryError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return _review_response(stored_review)


@router.get(
    "/reorder-recommendations/{recommendation_id}",
    response_model=ReorderRecommendationReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a stored reorder recommendation review",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Stored recommendation review not found."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid recommendation identifier."
        },
    },
)
def get_reorder_recommendation_review(
    recommendation_id: UUID,
    workflow_repository: WorkflowRepositoryDependency,
) -> ReorderRecommendationReviewResponse:
    """Retrieve a stored snapshot without recalculating any source data."""
    try:
        review = workflow_repository.get_review(recommendation_id)
    except RecommendationReviewNotFoundError as error:
        raise _review_not_found(error) from error
    return _review_response(review)


@router.post(
    "/reorder-recommendations/{recommendation_id}/approve",
    response_model=ReorderRecommendationReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a stored reorder recommendation",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Stored recommendation review not found."
        },
        status.HTTP_409_CONFLICT: {
            "description": "Decision conflicts with the terminal review state."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid identifier or approval details."
        },
    },
)
def approve_reorder_recommendation(
    recommendation_id: UUID,
    request: ApproveRecommendationRequest,
    workflow_repository: WorkflowRepositoryDependency,
    clock: ClockDependency,
) -> ReorderRecommendationReviewResponse:
    """Atomically approve a pending review or retry the same approval."""
    try:
        review = workflow_repository.approve_review(
            recommendation_id,
            decision_id=uuid4(),
            decided_by=request.decided_by,
            decided_at=clock.now(),
            approved_quantity=request.approved_quantity,
            note=request.note,
        )
    except RecommendationReviewNotFoundError as error:
        raise _review_not_found(error) from error
    except RecommendationReviewConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return _review_response(review)


@router.post(
    "/reorder-recommendations/{recommendation_id}/reject",
    response_model=ReorderRecommendationReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject a stored reorder recommendation",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Stored recommendation review not found."
        },
        status.HTTP_409_CONFLICT: {
            "description": "Decision conflicts with the terminal review state."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid identifier or rejection details."
        },
    },
)
def reject_reorder_recommendation(
    recommendation_id: UUID,
    request: RejectRecommendationRequest,
    workflow_repository: WorkflowRepositoryDependency,
    clock: ClockDependency,
) -> ReorderRecommendationReviewResponse:
    """Atomically reject a pending review or retry the same rejection."""
    try:
        review = workflow_repository.reject_review(
            recommendation_id,
            decision_id=uuid4(),
            decided_by=request.decided_by,
            decided_at=clock.now(),
            reason=request.reason,
        )
    except RecommendationReviewNotFoundError as error:
        raise _review_not_found(error) from error
    except RecommendationReviewConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return _review_response(review)
