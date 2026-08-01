"""Tests for the isolated in-memory product and inventory repository."""

from uuid import UUID

import pytest

from opsmind.domain.errors import (
    DuplicateSkuError,
    InventoryNotFoundError,
    ProductNotFoundError,
)
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
from opsmind.repositories.memory import InMemoryProductInventoryRepository

FIRST_ID = UUID("00000000-0000-0000-0000-000000000001")
SECOND_ID = UUID("00000000-0000-0000-0000-000000000002")
MISSING_ID = UUID("00000000-0000-0000-0000-000000000099")


def product(product_id: UUID = FIRST_ID, sku: str = "SENSOR-001") -> Product:
    """Create a valid product for repository tests."""
    return Product(
        id=product_id,
        sku=sku,
        name=f"Product {sku}",
        unit_of_measure="each",
        lead_time_days=7,
        is_active=True,
    )


def test_create_and_retrieve_product_by_uuid() -> None:
    repository = InMemoryProductInventoryRepository()
    created = repository.create_product(product())

    assert repository.get_product(FIRST_ID) is created


def test_duplicate_normalized_sku_is_rejected() -> None:
    repository = InMemoryProductInventoryRepository()
    repository.create_product(product())

    with pytest.raises(DuplicateSkuError) as error:
        repository.create_product(product(SECOND_ID, " sensor-001 "))

    assert error.value.sku == "SENSOR-001"


def test_products_are_listed_in_deterministic_sku_order() -> None:
    repository = InMemoryProductInventoryRepository()
    repository.create_product(product(FIRST_ID, "ZZZ-001"))
    repository.create_product(product(SECOND_ID, "AAA-001"))

    assert [item.sku for item in repository.list_products()] == [
        "AAA-001",
        "ZZZ-001",
    ]


def test_get_missing_product_raises_typed_error() -> None:
    repository = InMemoryProductInventoryRepository()

    with pytest.raises(ProductNotFoundError) as error:
        repository.get_product(MISSING_ID)

    assert error.value.product_id == MISSING_ID


def test_existing_product_initially_has_no_inventory() -> None:
    repository = InMemoryProductInventoryRepository()
    repository.create_product(product())

    with pytest.raises(InventoryNotFoundError) as error:
        repository.get_inventory(FIRST_ID)

    assert error.value.product_id == FIRST_ID


def test_inventory_can_be_set_and_replaced() -> None:
    repository = InMemoryProductInventoryRepository()
    repository.create_product(product())
    original = InventoryPosition(FIRST_ID, 100, 35)
    replacement = InventoryPosition(FIRST_ID, 20, 30)

    assert repository.set_inventory(original) is original
    assert repository.get_inventory(FIRST_ID) == original
    assert repository.set_inventory(replacement) is replacement
    assert repository.get_inventory(FIRST_ID) == replacement


def test_inventory_update_for_missing_product_is_rejected() -> None:
    repository = InMemoryProductInventoryRepository()
    inventory = InventoryPosition(MISSING_ID, 10, 2)

    with pytest.raises(ProductNotFoundError) as error:
        repository.set_inventory(inventory)

    assert error.value.product_id == MISSING_ID


def test_get_inventory_for_missing_product_is_distinct() -> None:
    repository = InMemoryProductInventoryRepository()

    with pytest.raises(ProductNotFoundError):
        repository.get_inventory(MISSING_ID)


def test_negative_available_inventory_is_preserved() -> None:
    repository = InMemoryProductInventoryRepository()
    repository.create_product(product())
    inventory = InventoryPosition(FIRST_ID, 20, 30)

    repository.set_inventory(inventory)

    assert repository.get_inventory(FIRST_ID).available_quantity == -10


def test_repository_instances_do_not_share_state() -> None:
    first_repository = InMemoryProductInventoryRepository()
    second_repository = InMemoryProductInventoryRepository()
    first_repository.create_product(product())

    assert [item.sku for item in first_repository.list_products()] == ["SENSOR-001"]
    assert second_repository.list_products() == ()
