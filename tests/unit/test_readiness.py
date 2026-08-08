"""Tests for bounded application readiness probes."""

from dataclasses import FrozenInstanceError
from typing import cast
from unittest.mock import MagicMock

import pytest
from sqlalchemy.engine import Engine

from opsmind.core.config import PersistenceBackend
from opsmind.readiness import (
    SUPPORTED_DATABASE_REVISION,
    MemoryReadinessProbe,
    PersistenceCheckStatus,
    PostgreSQLReadinessProbe,
    ReadinessResult,
    ReadinessStatus,
)


def postgresql_engine_result(
    revision: str | None,
) -> tuple[Engine, MagicMock]:
    """Create a typed mocked Engine returning one bounded revision value."""
    engine = MagicMock(spec=Engine)
    connection = engine.connect.return_value.__enter__.return_value
    connection.execute.return_value.scalar_one_or_none.return_value = revision
    return cast(Engine, engine), connection


def test_supported_database_revision_is_current_alembic_head() -> None:
    assert SUPPORTED_DATABASE_REVISION == "0006_workflow_persistence"


def test_readiness_result_is_immutable_and_slotted() -> None:
    result = ReadinessResult(
        status=ReadinessStatus.READY,
        backend=PersistenceBackend.MEMORY,
        persistence=PersistenceCheckStatus.READY,
    )

    assert result.__slots__ == ("status", "backend", "persistence")
    with pytest.raises(FrozenInstanceError):
        result.status = ReadinessStatus.NOT_READY  # type: ignore[misc]


def test_memory_readiness_returns_ready_without_collaborators() -> None:
    assert MemoryReadinessProbe().check_readiness() == ReadinessResult(
        status=ReadinessStatus.READY,
        backend=PersistenceBackend.MEMORY,
        persistence=PersistenceCheckStatus.READY,
    )


def test_postgresql_readiness_requires_exact_supported_revision() -> None:
    engine, connection = postgresql_engine_result(SUPPORTED_DATABASE_REVISION)

    result = PostgreSQLReadinessProbe(engine).check_readiness()

    assert result == ReadinessResult(
        status=ReadinessStatus.READY,
        backend=PersistenceBackend.POSTGRESQL,
        persistence=PersistenceCheckStatus.READY,
    )
    statement = connection.execute.call_args.args[0]
    assert str(statement) == "SELECT version_num FROM alembic_version"


@pytest.mark.parametrize("revision", [None, "0005_operational_data"])
def test_postgresql_readiness_rejects_missing_or_wrong_revision(
    revision: str | None,
) -> None:
    engine, _ = postgresql_engine_result(revision)

    assert PostgreSQLReadinessProbe(engine).check_readiness() == ReadinessResult(
        status=ReadinessStatus.NOT_READY,
        backend=PersistenceBackend.POSTGRESQL,
        persistence=PersistenceCheckStatus.NOT_READY,
    )


@pytest.mark.parametrize("failure_stage", ["connect", "query"])
def test_postgresql_readiness_bounds_connection_and_query_failures(
    failure_stage: str,
) -> None:
    secret = "postgresql://user:password@database.internal:5432/secret"
    engine = MagicMock(spec=Engine)
    if failure_stage == "connect":
        engine.connect.side_effect = RuntimeError(secret)
    else:
        connection = engine.connect.return_value.__enter__.return_value
        connection.execute.side_effect = RuntimeError(secret)

    result = PostgreSQLReadinessProbe(cast(Engine, engine)).check_readiness()

    assert result == ReadinessResult(
        status=ReadinessStatus.NOT_READY,
        backend=PersistenceBackend.POSTGRESQL,
        persistence=PersistenceCheckStatus.NOT_READY,
    )
    assert secret not in repr(result)
