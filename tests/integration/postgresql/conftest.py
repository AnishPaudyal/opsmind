"""Safe real-PostgreSQL fixtures initialized exclusively through Alembic."""

import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete
from sqlalchemy.engine import URL, Engine

from opsmind.persistence.postgresql.database import (
    SessionFactory,
    create_postgresql_engine,
    create_session_factory,
    dispose_engine,
    validate_test_database_url,
)
from opsmind.persistence.postgresql.models import (
    DemandObservationRow,
    InventoryPositionRow,
    ProductRow,
)
from opsmind.persistence.postgresql.repository import (
    PostgresProductInventoryRepository,
)

TEST_DATABASE_VARIABLE = "OPSMIND_TEST_DATABASE_URL"


@pytest.fixture(scope="session")
def postgresql_url() -> URL:
    """Return a safety-validated URL or skip local integration execution."""
    raw_url = os.environ.get(TEST_DATABASE_VARIABLE)
    if raw_url is None:
        pytest.skip(f"{TEST_DATABASE_VARIABLE} is not configured")
    try:
        return validate_test_database_url(raw_url)
    except ValueError as error:
        pytest.fail(f"Unsafe PostgreSQL integration configuration: {error}")


@pytest.fixture(scope="session")
def alembic_config(postgresql_url: URL) -> Config:
    """Create an Alembic configuration without rendering connection secrets."""
    configuration = Config("alembic.ini")
    configuration.attributes["opsmind_database_url"] = postgresql_url
    return configuration


@pytest.fixture(scope="session")
def postgresql_engine(
    postgresql_url: URL,
    alembic_config: Config,
) -> Iterator[Engine]:
    """Migrate a dedicated test database and expose one test-owned Engine."""
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    engine = create_postgresql_engine(postgresql_url)
    try:
        yield engine
    finally:
        command.upgrade(alembic_config, "head")
        dispose_engine(engine)


def _delete_operational_data(engine: Engine) -> None:
    with engine.begin() as connection:
        connection.execute(delete(DemandObservationRow))
        connection.execute(delete(InventoryPositionRow))
        connection.execute(delete(ProductRow))


@pytest.fixture
def clean_postgresql(postgresql_engine: Engine) -> Iterator[None]:
    """Delete test rows in dependency order before and after one test."""
    _delete_operational_data(postgresql_engine)
    try:
        yield
    finally:
        _delete_operational_data(postgresql_engine)


@pytest.fixture
def session_factory(
    postgresql_engine: Engine,
    clean_postgresql: None,
) -> SessionFactory:
    """Return a session factory after deterministic table cleanup."""
    return create_session_factory(postgresql_engine)


@pytest.fixture
def repository(
    session_factory: SessionFactory,
) -> PostgresProductInventoryRepository:
    """Return one repository using the dedicated integration database."""
    return PostgresProductInventoryRepository(session_factory)
