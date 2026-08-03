"""Real-PostgreSQL migration and runtime-schema tests."""

from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import inspect
from sqlalchemy.engine import URL, Engine

from opsmind.application import create_app
from opsmind.core.config import Environment, PersistenceBackend, Settings

EXPECTED_TABLES = {
    "products",
    "inventory_positions",
    "demand_observations",
    "recommendation_reviews",
    "recommendation_decisions",
    "recommendation_audit_events",
}


def test_initial_migration_has_expected_schema_and_is_idempotent(
    postgresql_engine: Engine,
    alembic_config: Config,
) -> None:
    command.upgrade(alembic_config, "head")
    command.upgrade(alembic_config, "head")
    inspector = inspect(postgresql_engine)

    assert EXPECTED_TABLES <= set(inspector.get_table_names())
    assert inspector.get_pk_constraint("products")["name"] == "pk_products"
    assert (
        inspector.get_pk_constraint("inventory_positions")["name"]
        == "pk_inventory_positions"
    )
    assert {item["name"] for item in inspector.get_unique_constraints("products")} == {
        "uq_products_sku"
    }
    assert {
        item["name"] for item in inspector.get_unique_constraints("demand_observations")
    } == {"uq_demand_observations_product_id"}
    assert {
        item["name"] for item in inspector.get_foreign_keys("inventory_positions")
    } == {"fk_inventory_positions_product_id_products"}
    assert {
        item["name"] for item in inspector.get_foreign_keys("demand_observations")
    } == {"fk_demand_observations_product_id_products"}
    assert {item["name"] for item in inspector.get_check_constraints("products")} == {
        "ck_products_lead_time_days_nonnegative",
        "ck_products_name_nonblank",
        "ck_products_sku_nonblank",
        "ck_products_unit_of_measure_nonblank",
    }
    assert {item["name"] for item in inspector.get_indexes("demand_observations")} >= {
        "ix_demand_observations_product_id"
    }


def test_downgrade_removes_tables_and_upgrade_restores_head(
    postgresql_engine: Engine,
    alembic_config: Config,
) -> None:
    try:
        command.downgrade(alembic_config, "base")
        assert EXPECTED_TABLES.isdisjoint(inspect(postgresql_engine).get_table_names())

        command.upgrade(alembic_config, "head")
        assert EXPECTED_TABLES <= set(inspect(postgresql_engine).get_table_names())
    finally:
        command.upgrade(alembic_config, "head")


def test_application_startup_does_not_create_missing_tables(
    postgresql_engine: Engine,
    postgresql_url: URL,
    alembic_config: Config,
) -> None:
    try:
        command.downgrade(alembic_config, "base")
        settings = Settings(
            environment=Environment.TEST,
            persistence_backend=PersistenceBackend.POSTGRESQL,
            database_url=SecretStr(
                postgresql_url.render_as_string(hide_password=False)
            ),
        )

        with TestClient(create_app(settings)) as client:
            assert client.get("/health").status_code == 200

        assert EXPECTED_TABLES.isdisjoint(inspect(postgresql_engine).get_table_names())
    finally:
        command.upgrade(alembic_config, "head")
