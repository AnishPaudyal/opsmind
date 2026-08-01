"""Versioned product and inventory endpoints."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from opsmind.api.dependencies import get_product_inventory_repository
from opsmind.domain.errors import (
    DuplicateSkuError,
    InventoryNotFoundError,
    ProductNotFoundError,
)
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.schemas.inventory import InventoryResponse, InventorySetRequest
from opsmind.schemas.product import ProductCreateRequest, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])

RepositoryDependency = Annotated[
    ProductInventoryRepository,
    Depends(get_product_inventory_repository),
]


def _product_response(product: Product) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        sku=product.sku,
        name=product.name,
        unit_of_measure=product.unit_of_measure,
        lead_time_days=product.lead_time_days,
        is_active=product.is_active,
    )


def _inventory_response(inventory: InventoryPosition) -> InventoryResponse:
    return InventoryResponse(
        product_id=inventory.product_id,
        on_hand_quantity=inventory.on_hand_quantity,
        allocated_quantity=inventory.allocated_quantity,
        available_quantity=inventory.available_quantity,
    )


def _product_not_found(error: ProductNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product '{error.product_id}' was not found.",
    )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product",
    responses={
        status.HTTP_409_CONFLICT: {"description": "Normalized SKU already exists."},
    },
)
def create_product(
    request: ProductCreateRequest,
    repository: RepositoryDependency,
) -> ProductResponse:
    """Create a validated product with a server-generated UUID."""
    try:
        product = Product(
            id=uuid4(),
            sku=request.sku,
            name=request.name,
            unit_of_measure=request.unit_of_measure,
            lead_time_days=request.lead_time_days,
            is_active=request.is_active,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    try:
        created_product = repository.create_product(product)
    except DuplicateSkuError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A product with SKU '{error.sku}' already exists.",
        ) from error
    return _product_response(created_product)


@router.get(
    "",
    response_model=list[ProductResponse],
    status_code=status.HTTP_200_OK,
    summary="List products",
)
def list_products(repository: RepositoryDependency) -> list[ProductResponse]:
    """List products in canonical SKU order."""
    return [_product_response(product) for product in repository.list_products()]


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a product",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Product not found."}},
)
def get_product(
    product_id: UUID,
    repository: RepositoryDependency,
) -> ProductResponse:
    """Retrieve a product by UUID."""
    try:
        product = repository.get_product(product_id)
    except ProductNotFoundError as error:
        raise _product_not_found(error) from error
    return _product_response(product)


@router.put(
    "/{product_id}/inventory",
    response_model=InventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Set product inventory",
    responses={status.HTTP_404_NOT_FOUND: {"description": "Product not found."}},
)
def set_inventory(
    product_id: UUID,
    request: InventorySetRequest,
    repository: RepositoryDependency,
) -> InventoryResponse:
    """Set or replace authoritative inventory quantities for a product."""
    inventory = InventoryPosition(
        product_id=product_id,
        on_hand_quantity=request.on_hand_quantity,
        allocated_quantity=request.allocated_quantity,
    )
    try:
        stored_inventory = repository.set_inventory(inventory)
    except ProductNotFoundError as error:
        raise _product_not_found(error) from error
    return _inventory_response(stored_inventory)


@router.get(
    "/{product_id}/inventory",
    response_model=InventoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get product inventory",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "description": "Product or inventory position not found."
        },
    },
)
def get_inventory(
    product_id: UUID,
    repository: RepositoryDependency,
) -> InventoryResponse:
    """Retrieve authoritative and calculated inventory quantities."""
    try:
        inventory = repository.get_inventory(product_id)
    except ProductNotFoundError as error:
        raise _product_not_found(error) from error
    except InventoryNotFoundError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inventory for product '{error.product_id}' was not found.",
        ) from error
    return _inventory_response(inventory)
