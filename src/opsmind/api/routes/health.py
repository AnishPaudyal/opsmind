"""Process-health endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from opsmind.core.config import Settings, get_settings
from opsmind.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check process health",
    description="Report deterministic health for the running API process.",
)
def read_health(settings: Annotated[Settings, Depends(get_settings)]) -> HealthResponse:
    """Return process-level health without checking downstream systems."""
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.environment,
    )
