"""PostgreSQL engine, metadata, and session-factory construction."""

from pydantic import SecretStr
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from opsmind.core.config import parse_postgresql_database_url

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Authoritative declarative base for PostgreSQL persistence models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


SessionFactory = sessionmaker[Session]

POSTGRESQL_CONNECT_TIMEOUT_SECONDS = 10


def create_postgresql_engine(database_url: SecretStr | str | URL) -> Engine:
    """Create a synchronous engine without connecting or exposing credentials."""
    url = parse_postgresql_database_url(database_url)
    return create_engine(
        url,
        hide_parameters=True,
        pool_pre_ping=True,
        connect_args={"connect_timeout": POSTGRESQL_CONNECT_TIMEOUT_SECONDS},
    )


def create_session_factory(engine: Engine) -> SessionFactory:
    """Create the short-lived Session factory used by repository operations."""
    return sessionmaker(
        bind=engine,
        class_=Session,
        autoflush=False,
        expire_on_commit=False,
    )


def dispose_engine(engine: Engine) -> None:
    """Release connections owned by one application engine."""
    engine.dispose()


def validate_test_database_url(database_url: SecretStr | str | URL) -> URL:
    """Reject destructive test use outside a clearly local test database."""
    url = parse_postgresql_database_url(database_url)
    database_name = url.database or ""
    if not database_name.endswith(("_test", "_testing")):
        raise ValueError("test database name must end in _test or _testing")
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("test database host must be local or loopback")
    return url
