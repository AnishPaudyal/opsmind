"""Application readiness contracts and persistence probes."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.engine import Engine

from opsmind.core.config import PersistenceBackend

SUPPORTED_DATABASE_REVISION = "0006_workflow_persistence"


class ReadinessStatus(StrEnum):
    """Bounded overall readiness values."""

    READY = "ready"
    NOT_READY = "not_ready"


class PersistenceCheckStatus(StrEnum):
    """Bounded persistence readiness values."""

    READY = "ready"
    NOT_READY = "not_ready"


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """One bounded application readiness result."""

    status: ReadinessStatus
    backend: PersistenceBackend
    persistence: PersistenceCheckStatus


class ReadinessProbe(Protocol):
    """Application-bound readiness behavior."""

    def check_readiness(self) -> ReadinessResult:
        """Return the current bounded readiness result."""
        ...


class MemoryReadinessProbe:
    """Deterministic readiness for process-local memory persistence."""

    def check_readiness(self) -> ReadinessResult:
        """Return ready without performing I/O."""
        return ReadinessResult(
            status=ReadinessStatus.READY,
            backend=PersistenceBackend.MEMORY,
            persistence=PersistenceCheckStatus.READY,
        )


class PostgreSQLReadinessProbe:
    """Connectivity and schema-revision readiness for PostgreSQL."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def check_readiness(self) -> ReadinessResult:
        """Return ready only when PostgreSQL is at the supported revision."""
        try:
            with self._engine.connect() as connection:
                revision = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one_or_none()
        except Exception:
            return self._not_ready()

        if revision != SUPPORTED_DATABASE_REVISION:
            return self._not_ready()

        return ReadinessResult(
            status=ReadinessStatus.READY,
            backend=PersistenceBackend.POSTGRESQL,
            persistence=PersistenceCheckStatus.READY,
        )

    @staticmethod
    def _not_ready() -> ReadinessResult:
        return ReadinessResult(
            status=ReadinessStatus.NOT_READY,
            backend=PersistenceBackend.POSTGRESQL,
            persistence=PersistenceCheckStatus.NOT_READY,
        )
