"""Real-PostgreSQL product repository and concurrency tests."""

from dataclasses import FrozenInstanceError
from threading import Barrier, Thread
from uuid import UUID

import pytest
from sqlalchemy import func, select

from opsmind.domain.errors import DuplicateSkuError, ProductNotFoundError
from opsmind.domain.product import Product
from opsmind.persistence.postgresql.database import SessionFactory
from opsmind.persistence.postgresql.models import ProductRow
from opsmind.persistence.postgresql.repository import (
    PostgresProductInventoryRepository,
)
from opsmind.repositories.product_inventory import ProductInventoryRepository

FIRST_ID = UUID("00000000-0000-0000-0000-000000000001")
SECOND_ID = UUID("00000000-0000-0000-0000-000000000002")
THIRD_ID = UUID("00000000-0000-0000-0000-000000000003")
MISSING_ID = UUID("00000000-0000-0000-0000-000000000099")


def product(product_id: UUID, sku: str) -> Product:
    return Product(product_id, sku, f"Product {sku}", "each", 5, True)


def test_repository_satisfies_protocol_and_persists_across_instances(
    repository: PostgresProductInventoryRepository,
    session_factory: SessionFactory,
) -> None:
    protocol_repository: ProductInventoryRepository = repository
    created = protocol_repository.create_product(product(FIRST_ID, " sensor-001 "))
    second_repository = PostgresProductInventoryRepository(session_factory)

    assert created.sku == "SENSOR-001"
    assert second_repository.get_product(FIRST_ID) == created
    with pytest.raises(FrozenInstanceError):
        setattr(created, "sku", "CHANGED")  # noqa: B010


def test_listing_and_missing_behavior_match_memory_repository(
    repository: PostgresProductInventoryRepository,
) -> None:
    repository.create_product(product(FIRST_ID, "ZETA"))
    repository.create_product(product(SECOND_ID, "ALPHA"))

    assert [item.sku for item in repository.list_products()] == ["ALPHA", "ZETA"]
    with pytest.raises(ProductNotFoundError) as error:
        repository.get_product(MISSING_ID)
    assert error.value.product_id == MISSING_ID


def test_duplicate_transaction_rolls_back_and_repository_remains_usable(
    repository: PostgresProductInventoryRepository,
) -> None:
    repository.create_product(product(FIRST_ID, "sensor-001"))

    with pytest.raises(DuplicateSkuError) as error:
        repository.create_product(product(SECOND_ID, " SENSOR-001 "))

    assert error.value.sku == "SENSOR-001"
    assert repository.create_product(product(THIRD_ID, "ACTUATOR-001")).id == THIRD_ID


def test_canonical_duplicate_concurrency_has_one_winner(
    repository: PostgresProductInventoryRepository,
    session_factory: SessionFactory,
) -> None:
    barrier = Barrier(2)
    outcomes: list[str] = []

    def create(candidate: Product) -> None:
        worker_repository = PostgresProductInventoryRepository(session_factory)
        barrier.wait()
        try:
            worker_repository.create_product(candidate)
            outcomes.append("created")
        except DuplicateSkuError:
            outcomes.append("duplicate")

    threads = [
        Thread(target=create, args=(product(FIRST_ID, "sensor-001"),)),
        Thread(target=create, args=(product(SECOND_ID, "SENSOR-001"),)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    with session_factory() as session:
        row_count = session.scalar(select(func.count()).select_from(ProductRow))

    assert sorted(outcomes) == ["created", "duplicate"]
    assert row_count == 1
    assert repository.create_product(product(THIRD_ID, "ACTUATOR-001")).id == THIRD_ID
