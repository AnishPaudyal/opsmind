"""Unit tests for secret-safe PostgreSQL construction and test safety."""

import pytest
from pydantic import SecretStr

from opsmind.persistence.postgresql.database import (
    create_postgresql_engine,
    create_session_factory,
    dispose_engine,
    validate_test_database_url,
)


def test_engine_construction_is_lazy_and_hides_password() -> None:
    password = "never-render-this-password"
    engine = create_postgresql_engine(
        SecretStr(f"postgresql+psycopg://opsmind:{password}@127.0.0.1:1/opsmind")
    )

    try:
        assert password not in repr(engine.url)
        assert password not in str(engine.url)
        assert engine.hide_parameters is True
    finally:
        dispose_engine(engine)


def test_session_factory_uses_required_lifecycle_settings() -> None:
    engine = create_postgresql_engine(
        "postgresql+psycopg://opsmind:development-only@127.0.0.1:1/opsmind"
    )

    try:
        session_factory = create_session_factory(engine)
        assert session_factory.kw["autoflush"] is False
        assert session_factory.kw["expire_on_commit"] is False
        assert session_factory.kw["bind"] is engine
    finally:
        dispose_engine(engine)


@pytest.mark.parametrize("suffix", ["_test", "_testing"])
def test_test_database_gate_accepts_local_test_names(suffix: str) -> None:
    url = validate_test_database_url(
        f"postgresql+psycopg://opsmind:local@127.0.0.1/opsmind{suffix}"
    )

    assert url.database == f"opsmind{suffix}"


@pytest.mark.parametrize("database_name", ["opsmind", "production", "test"])
def test_test_database_gate_rejects_non_test_database_names(
    database_name: str,
) -> None:
    with pytest.raises(
        ValueError,
        match=r"^test database name must end in _test or _testing$",
    ):
        validate_test_database_url(
            "postgresql+psycopg://opsmind:local@127.0.0.1/" + database_name
        )


def test_test_database_gate_rejects_nonlocal_host_without_revealing_url() -> None:
    url = "postgresql+psycopg://user:sensitive@database.example/opsmind_test"

    with pytest.raises(ValueError) as error:
        validate_test_database_url(url)

    assert str(error.value) == "test database host must be local or loopback"
    assert url not in str(error.value)
