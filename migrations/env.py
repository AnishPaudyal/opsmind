"""Alembic environment for the OpsMind PostgreSQL schema."""

from logging.config import fileConfig
from os import environ

from alembic import context
from pydantic import SecretStr
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL

from opsmind.core.config import parse_postgresql_database_url
from opsmind.persistence.postgresql import models as _models  # noqa: F401
from opsmind.persistence.postgresql.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> URL:
    configured_url = config.attributes.get("opsmind_database_url")
    if isinstance(configured_url, URL):
        return configured_url
    if isinstance(configured_url, (SecretStr, str)):
        return parse_postgresql_database_url(configured_url)

    raw_url = environ.get("OPSMIND_DATABASE_URL")
    if raw_url is None:
        raise RuntimeError(
            "OPSMIND_DATABASE_URL is required for Alembic migration commands."
        )
    return parse_postgresql_database_url(SecretStr(raw_url))


def run_migrations_offline() -> None:
    """Run migrations without creating an Engine."""
    url = _database_url()
    context.configure(
        url=url.render_as_string(hide_password=False),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with one disposable migration Engine."""
    connectable = create_engine(
        _database_url(),
        hide_parameters=True,
        poolclass=pool.NullPool,
    )

    try:
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata,
                compare_type=True,
            )

            with context.begin_transaction():
                context.run_migrations()
    finally:
        connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
