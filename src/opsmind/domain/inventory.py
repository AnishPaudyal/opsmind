"""Inventory domain model and available-quantity calculation."""

from dataclasses import dataclass
from uuid import UUID


def calculate_available_quantity(
    on_hand_quantity: int,
    allocated_quantity: int,
) -> int:
    """Calculate inventory remaining after allocations."""
    if on_hand_quantity < 0:
        raise ValueError("on_hand_quantity must be non-negative")
    if allocated_quantity < 0:
        raise ValueError("allocated_quantity must be non-negative")
    return on_hand_quantity - allocated_quantity


@dataclass(frozen=True, slots=True)
class InventoryPosition:
    """Authoritative inventory quantities for one product."""

    product_id: UUID
    on_hand_quantity: int
    allocated_quantity: int

    def __post_init__(self) -> None:
        calculate_available_quantity(
            self.on_hand_quantity,
            self.allocated_quantity,
        )

    @property
    def available_quantity(self) -> int:
        """Calculate the current quantity remaining after allocations."""
        return calculate_available_quantity(
            self.on_hand_quantity,
            self.allocated_quantity,
        )
