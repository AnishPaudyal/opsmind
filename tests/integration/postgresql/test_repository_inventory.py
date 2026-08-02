"""Real-PostgreSQL inventory persistence and concurrency tests."""

from threading import Barrier, Thread
from uuid import UUID

import pytest
from sqlalchemy import func, select

from opsmind.domain.errors import InventoryNotFoundError, ProductNotFoundError
from opsmind.domain.inventory import InventoryPosition
from opsmind.domain.product import Product
from opsmind.persistence.postgresql.database import SessionFactory
from opsmind.persistence.postgresql.models import InventoryPositionRow
from opsmind.persistence.postgresql.repository import (
    PostgresProductInventoryRepository,
)

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")
MISSING_ID = UUID("00000000-0000-0000-0000-000000000099")


def store_product(repository: PostgresProductInventoryRepository) -> None:
    repository.create_product(
        Product(PRODUCT_ID, "SENSOR-001", "Sensor", "units", 5, True)
    )


def test_inventory_persists_replaces_one_row_and_derives_negative_availability(
    repository: PostgresProductInventoryRepository,
    session_factory: SessionFactory,
) -> None:
    store_product(repository)
    repository.set_inventory(InventoryPosition(PRODUCT_ID, 20, 5))
    replacement = InventoryPosition(PRODUCT_ID, 10, 30)
    repository.set_inventory(replacement)
    second_repository = PostgresProductInventoryRepository(session_factory)

    assert second_repository.get_inventory(PRODUCT_ID) == replacement
    assert second_repository.get_inventory(PRODUCT_ID).available_quantity == -20
    with session_factory() as session:
        row_count = session.scalar(
            select(func.count()).select_from(InventoryPositionRow)
        )
    assert row_count == 1


def test_inventory_distinguishes_missing_product_and_position(
    repository: PostgresProductInventoryRepository,
) -> None:
    with pytest.raises(ProductNotFoundError):
        repository.set_inventory(InventoryPosition(MISSING_ID, 1, 0))
    with pytest.raises(ProductNotFoundError):
        repository.get_inventory(MISSING_ID)

    store_product(repository)
    with pytest.raises(InventoryNotFoundError):
        repository.get_inventory(PRODUCT_ID)


def test_concurrent_complete_inventory_upserts_leave_one_unmixed_row(
    repository: PostgresProductInventoryRepository,
    session_factory: SessionFactory,
) -> None:
    store_product(repository)
    barrier = Barrier(2)
    positions = (
        InventoryPosition(PRODUCT_ID, 100, 10),
        InventoryPosition(PRODUCT_ID, 40, 35),
    )
    outcomes: list[InventoryPosition] = []

    def write(position: InventoryPosition) -> None:
        worker_repository = PostgresProductInventoryRepository(session_factory)
        barrier.wait()
        outcomes.append(worker_repository.set_inventory(position))

    threads = [Thread(target=write, args=(position,)) for position in positions]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    final_position = repository.get_inventory(PRODUCT_ID)
    with session_factory() as session:
        row_count = session.scalar(
            select(func.count()).select_from(InventoryPositionRow)
        )

    assert len(outcomes) == 2
    assert final_position in positions
    assert row_count == 1
    assert repository.get_product(PRODUCT_ID).sku == "SENSOR-001"
