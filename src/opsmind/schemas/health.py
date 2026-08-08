"""Health endpoint schemas."""

from typing import Literal

from pydantic import BaseModel

from opsmind.core.config import Environment, PersistenceBackend
from opsmind.readiness import PersistenceCheckStatus, ReadinessStatus


class HealthResponse(BaseModel):
    """Public process-health response."""

    status: Literal["ok"]
    service: str
    environment: Environment


class ReadinessChecks(BaseModel):
    """Bounded public dependency-readiness checks."""

    persistence: PersistenceCheckStatus


class ReadinessResponse(BaseModel):
    """Bounded public application-readiness response."""

    status: ReadinessStatus
    service: str
    environment: Environment
    backend: PersistenceBackend
    checks: ReadinessChecks
