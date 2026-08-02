"""Real-PostgreSQL atomic demand persistence and concurrency tests."""

from datetime import date
from threading import Barrier, Thread
from uuid import UUID

import pytest
from sqlalchemy import func, select

from opsmind.domain.demand import DemandObservation
from opsmind.domain.errors import DuplicateDemandDateError, ProductNotFoundError
from opsmind.domain.product import Product
from opsmind.persistence.postgresql.database import SessionFactory
from opsmind.persistence.postgresql.models import DemandObservationRow
from opsmind.persistence.postgresql.repository import (
    PostgresProductInventoryRepository,
)

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")
OTHER_PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000002")
MISSING_ID = UUID("00000000-0000-0000-0000-000000000099")


def store_products(repository: PostgresProductInventoryRepository) -> None:
    repository.create_product(
        Product(PRODUCT_ID, "SENSOR-001", "Sensor", "units", 5, True)
    )
    repository.create_product(
        Product(OTHER_PRODUCT_ID, "SENSOR-002", "Sensor 2", "units", 5, True)
    )


def observation(day: int, quantity: int = 1) -> DemandObservation:
    return DemandObservation(PRODUCT_ID, date(2026, 7, day), quantity)


def test_demand_persists_ids_zero_order_and_inclusive_filters(
    repository: PostgresProductInventoryRepository,
    session_factory: SessionFactory,
) -> None:
    store_products(repository)
    submitted = (observation(3, 9), observation(1, 12), observation(2, 0))
    stored = repository.add_demand_observations(PRODUCT_ID, submitted)
    second_repository = PostgresProductInventoryRepository(session_factory)

    assert [item.demand_date.day for item in stored] == [1, 2, 3]
    assert {item.id for item in stored} == {item.id for item in submitted}
    assert second_repository.list_demand_observations(PRODUCT_ID)[1].quantity == 0
    assert [
        item.demand_date.day
        for item in second_repository.list_demand_observations(
            PRODUCT_ID,
            start_date=date(2026, 7, 2),
            end_date=date(2026, 7, 3),
        )
    ] == [2, 3]
    assert (
        second_repository.list_demand_observations(
            PRODUCT_ID,
            start_date=date(2026, 8, 1),
        )
        == ()
    )


def test_demand_missing_product_and_per_product_uniqueness(
    repository: PostgresProductInventoryRepository,
) -> None:
    with pytest.raises(ProductNotFoundError):
        repository.add_demand_observations(
            MISSING_ID,
            (DemandObservation(MISSING_ID, date(2026, 7, 1), 1),),
        )

    store_products(repository)
    repository.add_demand_observations(PRODUCT_ID, (observation(1, 12),))
    other = DemandObservation(OTHER_PRODUCT_ID, date(2026, 7, 1), 7)
    assert repository.add_demand_observations(OTHER_PRODUCT_ID, (other,)) == (other,)


def test_conflicting_batch_rolls_back_fully_and_future_write_succeeds(
    repository: PostgresProductInventoryRepository,
) -> None:
    store_products(repository)
    existing = observation(1, 12)
    repository.add_demand_observations(PRODUCT_ID, (existing,))

    with pytest.raises(DuplicateDemandDateError) as error:
        repository.add_demand_observations(
            PRODUCT_ID,
            (observation(2, 18), observation(1, 99)),
        )

    assert error.value.demand_date == date(2026, 7, 1)
    assert repository.list_demand_observations(PRODUCT_ID) == (existing,)
    repository.add_demand_observations(PRODUCT_ID, (observation(3, 9),))
    assert [
        item.demand_date.day for item in repository.list_demand_observations(PRODUCT_ID)
    ] == [1, 3]


def test_duplicate_inside_batch_is_rejected_before_database_write(
    repository: PostgresProductInventoryRepository,
) -> None:
    store_products(repository)
    with pytest.raises(DuplicateDemandDateError):
        repository.add_demand_observations(
            PRODUCT_ID,
            (observation(1, 1), observation(1, 2)),
        )
    assert repository.list_demand_observations(PRODUCT_ID) == ()


def test_concurrent_duplicate_date_has_one_winner(
    repository: PostgresProductInventoryRepository,
    session_factory: SessionFactory,
) -> None:
    store_products(repository)
    barrier = Barrier(2)
    outcomes: list[str] = []

    def insert_quantity(quantity: int) -> None:
        worker_repository = PostgresProductInventoryRepository(session_factory)
        barrier.wait()
        try:
            worker_repository.add_demand_observations(
                PRODUCT_ID,
                (observation(1, quantity),),
            )
            outcomes.append("created")
        except DuplicateDemandDateError:
            outcomes.append("duplicate")

    threads = [Thread(target=insert_quantity, args=(quantity,)) for quantity in (4, 8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with session_factory() as session:
        row_count = session.scalar(
            select(func.count()).select_from(DemandObservationRow)
        )

    assert sorted(outcomes) == ["created", "duplicate"]
    assert row_count == 1
    assert repository.list_demand_observations(PRODUCT_ID)[0].quantity in {4, 8}
