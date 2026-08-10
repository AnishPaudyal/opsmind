"""FastAPI dependencies for application-bound services and security."""

from typing import Annotated, Any

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from opsmind.core.clock import Clock
from opsmind.readiness import ReadinessProbe
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.repositories.recommendation_workflow import (
    RecommendationWorkflowRepository,
)
from opsmind.security import (
    AuthenticationError,
    Authenticator,
    Permission,
    TrustedPrincipal,
)

BEARER_SCHEME_NAME = "BearerAuth"
AUTHENTICATION_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
    status.HTTP_403_FORBIDDEN: {"description": "Insufficient permission."},
}

_bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name=BEARER_SCHEME_NAME,
    description="Signed bearer access token validated by OpsMind.",
)


def get_product_inventory_repository() -> ProductInventoryRepository:
    """Return the application-bound product and inventory repository."""
    raise RuntimeError("Product inventory repository is not configured")


def get_recommendation_workflow_repository() -> RecommendationWorkflowRepository:
    """Return the application-bound recommendation workflow repository."""
    raise RuntimeError("Recommendation workflow repository is not configured")


def get_clock() -> Clock:
    """Return the application-bound workflow clock."""
    raise RuntimeError("Clock is not configured")


def get_readiness_probe() -> ReadinessProbe:
    """Return the application-bound readiness probe."""
    raise RuntimeError("Readiness probe is not configured")


def get_authenticator() -> Authenticator:
    """Return the application-bound bearer-token authenticator."""
    raise RuntimeError("Authenticator is not configured")


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_principal(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(_bearer_scheme),
    ],
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
) -> TrustedPrincipal:
    """Authenticate one bearer credential without exposing failure detail."""
    if (
        len(request.headers.getlist("authorization")) != 1
        or credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise _unauthorized()
    try:
        return authenticator.authenticate(credentials.credentials)
    except AuthenticationError:
        raise _unauthorized() from None


def _require_permission(
    principal: TrustedPrincipal,
    permission: Permission,
) -> TrustedPrincipal:
    if permission not in principal.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permission.",
        )
    return principal


def require_business_read(
    principal: Annotated[TrustedPrincipal, Depends(get_current_principal)],
) -> TrustedPrincipal:
    """Require permission to read business data and evidence."""
    return _require_permission(principal, Permission.BUSINESS_READ)


def require_business_write(
    principal: Annotated[TrustedPrincipal, Depends(get_current_principal)],
) -> TrustedPrincipal:
    """Require permission to mutate operational business state."""
    return _require_permission(principal, Permission.BUSINESS_WRITE)


def require_recommendation_decide(
    principal: Annotated[TrustedPrincipal, Depends(get_current_principal)],
) -> TrustedPrincipal:
    """Require permission to make a terminal recommendation decision."""
    return _require_permission(principal, Permission.RECOMMENDATION_DECIDE)


BusinessReadPrincipal = Annotated[
    TrustedPrincipal,
    Depends(require_business_read),
]
BusinessWritePrincipal = Annotated[
    TrustedPrincipal,
    Depends(require_business_write),
]
RecommendationDecidePrincipal = Annotated[
    TrustedPrincipal,
    Depends(require_recommendation_decide),
]
