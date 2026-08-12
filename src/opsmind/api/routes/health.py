"""Process-health endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status
from starlette.responses import JSONResponse

from opsmind.api.dependencies import get_readiness_probe
from opsmind.core.config import Settings, get_settings
from opsmind.observability import ERROR_CATEGORY_STATE_KEY, ErrorCategory
from opsmind.readiness import ReadinessProbe, ReadinessStatus
from opsmind.schemas.health import HealthResponse, ReadinessChecks, ReadinessResponse

router = APIRouter(tags=["health"])

BUILD_REVISION_HEADER = "X-OpsMind-Revision"


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_200_OK: {
            "headers": {
                BUILD_REVISION_HEADER: {
                    "description": (
                        "Full Git revision of the running release when build "
                        "identity is available."
                    ),
                    "schema": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{40}$",
                    },
                }
            }
        }
    },
    summary="Check process health",
    description="Report deterministic health for the running API process.",
)
def read_health(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Return process-level health without checking downstream systems."""
    if settings.build_revision is not None:
        response.headers[BUILD_REVISION_HEADER] = settings.build_revision

    return HealthResponse(
        status="ok",
        service=settings.service_name,
        environment=settings.environment,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": ReadinessResponse,
            "description": "Configured application dependencies are not ready.",
        }
    },
    summary="Check application readiness",
    description="Report bounded readiness for configured application dependencies.",
)
def read_readiness(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
    readiness_probe: Annotated[ReadinessProbe, Depends(get_readiness_probe)],
) -> ReadinessResponse | JSONResponse:
    """Return bounded dependency readiness without exposing internal failures."""
    result = readiness_probe.check_readiness()
    response = ReadinessResponse(
        status=result.status,
        service=settings.service_name,
        environment=settings.environment,
        backend=result.backend,
        checks=ReadinessChecks(persistence=result.persistence),
    )
    if result.status is ReadinessStatus.READY:
        return response

    request.scope["state"][ERROR_CATEGORY_STATE_KEY] = (
        ErrorCategory.DEPENDENCY_UNAVAILABLE
    )
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content=response.model_dump(mode="json"),
    )
