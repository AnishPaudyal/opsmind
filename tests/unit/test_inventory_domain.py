"""Tests for inventory domain rules."""

from uuid import UUID

import pytest

from opsmind.domain.inventory import InventoryPosition, calculate_available_quantity

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")


@pytest.mark.parametrize(
    ("on_hand_quantity", "allocated_quantity", "expected"),
    [(10, 3, 7), (5, 5, 0), (3, 8, -5)],
)
def test_calculate_available_quantity(
    on_hand_quantity: int,
    allocated_quantity: int,
    expected: int,
) -> None:
    assert (
        calculate_available_quantity(on_hand_quantity, allocated_quantity) == expected
    )


def test_calculate_available_quantity_rejects_negative_on_hand() -> None:
    with pytest.raises(
        ValueError,
        match=r"^on_hand_quantity must be non-negative$",
    ):
        calculate_available_quantity(-1, 0)


def test_calculate_available_quantity_rejects_negative_allocated() -> None:
    with pytest.raises(
        ValueError,
        match=r"^allocated_quantity must be non-negative$",
    ):
        calculate_available_quantity(0, -1)


def test_inventory_position_calculates_availability_without_storing_it() -> None:
    inventory = InventoryPosition(
        product_id=PRODUCT_ID,
        on_hand_quantity=20,
        allocated_quantity=30,
    )

    assert inventory.available_quantity == -10
    assert "available_quantity" not in inventory.__slots__


def test_inventory_position_applies_quantity_validation() -> None:
    with pytest.raises(
        ValueError,
        match=r"^on_hand_quantity must be non-negative$",
    ):
        InventoryPosition(
            product_id=PRODUCT_ID,
            on_hand_quantity=-1,
            allocated_quantity=0,
        )
