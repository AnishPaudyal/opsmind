"""Tests for atomic in-memory demand-history behavior."""

from dataclasses import FrozenInstanceError
from datetime import date
from uuid import UUID

import pytest

from opsmind.domain.demand import DemandObservation
from opsmind.domain.errors import DuplicateDemandDateError, ProductNotFoundError
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
from opsmind.repositories.memory import InMemoryProductInventoryRepository

FIRST_ID = UUID("00000000-0000-0000-0000-000000000001")
SECOND_ID = UUID("00000000-0000-0000-0000-000000000002")
MISSING_ID = UUID("00000000-0000-0000-0000-000000000099")


def product(product_id: UUID, sku: str) -> Product:
    """Create a valid product for repository tests."""
    return Product(product_id, sku, f"Product {sku}", "each", 7, True)


def observation(
    demand_date: date,
    quantity: int,
    product_id: UUID = FIRST_ID,
) -> DemandObservation:
    """Create one demand observation."""
    return DemandObservation(product_id, demand_date, quantity)


def repository_with_products() -> InMemoryProductInventoryRepository:
    """Create a repository containing two products."""
    repository = InMemoryProductInventoryRepository()
    repository.create_product(product(FIRST_ID, "SENSOR-001"))
    repository.create_product(product(SECOND_ID, "ACTUATOR-001"))
    return repository


def test_add_demand_for_existing_product_returns_chronological_tuple() -> None:
    repository = repository_with_products()
    submitted = (
        observation(date(2026, 7, 2), 18),
        observation(date(2026, 7, 1), 12),
    )

    stored = repository.add_demand_observations(FIRST_ID, submitted)

    assert isinstance(stored, tuple)
    assert [item.demand_date.day for item in stored] == [1, 2]
    assert [
        item.demand_date.day for item in repository.list_demand_observations(FIRST_ID)
    ] == [1, 2]


def test_missing_product_rejects_demand_insertion() -> None:
    repository = InMemoryProductInventoryRepository()

    with pytest.raises(ProductNotFoundError) as error:
        repository.add_demand_observations(
            MISSING_ID,
            (observation(date(2026, 7, 1), 12, MISSING_ID),),
        )

    assert error.value.product_id == MISSING_ID


def test_existing_product_without_demand_returns_empty_tuple() -> None:
    repository = repository_with_products()

    assert repository.list_demand_observations(FIRST_ID) == ()


def test_missing_product_rejects_demand_retrieval() -> None:
    repository = InMemoryProductInventoryRepository()

    with pytest.raises(ProductNotFoundError):
        repository.list_demand_observations(MISSING_ID)


def test_zero_demand_is_preserved() -> None:
    repository = repository_with_products()
    repository.add_demand_observations(
        FIRST_ID,
        (observation(date(2026, 7, 1), 0),),
    )

    assert repository.list_demand_observations(FIRST_ID)[0].quantity == 0


def test_same_date_is_independent_between_products() -> None:
    repository = repository_with_products()
    demand_date = date(2026, 7, 1)

    repository.add_demand_observations(
        FIRST_ID,
        (observation(demand_date, 12),),
    )
    repository.add_demand_observations(
        SECOND_ID,
        (observation(demand_date, 7, SECOND_ID),),
    )

    assert repository.list_demand_observations(FIRST_ID)[0].quantity == 12
    assert repository.list_demand_observations(SECOND_ID)[0].quantity == 7


def test_duplicate_date_inside_batch_is_rejected_atomically() -> None:
    repository = repository_with_products()
    demand_date = date(2026, 7, 1)

    with pytest.raises(DuplicateDemandDateError):
        repository.add_demand_observations(
            FIRST_ID,
            (observation(demand_date, 12), observation(demand_date, 18)),
        )

    assert repository.list_demand_observations(FIRST_ID) == ()


def test_existing_duplicate_rejects_complete_batch_without_partial_mutation() -> None:
    repository = repository_with_products()
    existing = observation(date(2026, 7, 1), 12)
    new = observation(date(2026, 7, 2), 18)
    repository.add_demand_observations(FIRST_ID, (existing,))

    with pytest.raises(DuplicateDemandDateError) as error:
        repository.add_demand_observations(FIRST_ID, (new, existing))

    assert error.value.demand_date == existing.demand_date
    assert repository.list_demand_observations(FIRST_ID) == (existing,)


@pytest.mark.parametrize(
    ("start_date", "end_date", "expected_days"),
    [
        (date(2026, 7, 2), None, [2, 3]),
        (None, date(2026, 7, 2), [1, 2]),
        (date(2026, 7, 2), date(2026, 7, 3), [2, 3]),
        (date(2026, 7, 2), date(2026, 7, 2), [2]),
        (date(2026, 8, 1), date(2026, 8, 31), []),
    ],
)
def test_inclusive_demand_date_filters(
    start_date: date | None,
    end_date: date | None,
    expected_days: list[int],
) -> None:
    repository = repository_with_products()
    repository.add_demand_observations(
        FIRST_ID,
        tuple(observation(date(2026, 7, day), day) for day in (3, 1, 2)),
    )

    result = repository.list_demand_observations(
        FIRST_ID,
        start_date=start_date,
        end_date=end_date,
    )

    assert [item.demand_date.day for item in result] == expected_days


def test_returned_state_is_immutable_and_does_not_expose_internal_mappings() -> None:
    repository = repository_with_products()
    stored = observation(date(2026, 7, 1), 12)
    repository.add_demand_observations(FIRST_ID, (stored,))
    returned = repository.list_demand_observations(FIRST_ID)

    with pytest.raises(FrozenInstanceError):
        setattr(returned[0], "quantity", 99)  # noqa: B010
    returned += (observation(date(2026, 7, 2), 18),)

    assert repository.list_demand_observations(FIRST_ID) == (stored,)


def test_repository_instances_do_not_share_demand() -> None:
    first_repository = repository_with_products()
    second_repository = repository_with_products()
    first_repository.add_demand_observations(
        FIRST_ID,
        (observation(date(2026, 7, 1), 12),),
    )

    assert len(first_repository.list_demand_observations(FIRST_ID)) == 1
    assert second_repository.list_demand_observations(FIRST_ID) == ()


def test_product_and_inventory_behavior_remains_available() -> None:
    repository = repository_with_products()
    inventory = InventoryPosition(FIRST_ID, 20, 30)

    assert repository.get_product(FIRST_ID).sku == "SENSOR-001"
    repository.set_inventory(inventory)
    assert repository.get_inventory(FIRST_ID).available_quantity == -10
