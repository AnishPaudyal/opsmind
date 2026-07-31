"""Health endpoint schemas."""

from typing import Literal

from pydantic import BaseModel

from opsmind.core.config import Environment


class HealthResponse(BaseModel):
    """Public process-health response."""

    status: Literal["ok"]
    service: str
    environment: Environment
