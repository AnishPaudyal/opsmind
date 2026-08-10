"""Explicit deterministic security helpers for authenticated tests."""

from dataclasses import dataclass

from fastapi import FastAPI
from fastapi.testclient import TestClient

from opsmind.application import create_app
from opsmind.core.clock import Clock
from opsmind.core.config import Settings
from opsmind.readiness import ReadinessProbe
from opsmind.repositories.product_inventory import ProductInventoryRepository
from opsmind.repositories.recommendation_workflow import (
    RecommendationWorkflowRepository,
)
from opsmind.security import AuthenticationError, Permission, TrustedPrincipal

TEST_BEARER_TOKEN = "synthetic-opsmind-test-token"
TEST_PRINCIPAL_ID = "Reviewer"
ALL_TEST_PERMISSIONS = frozenset(Permission)


@dataclass(frozen=True, slots=True)
class StaticTestAuthenticator:
    """Authenticate one synthetic token as one explicit test principal."""

    principal: TrustedPrincipal
    token: str = TEST_BEARER_TOKEN

    def authenticate(self, token: str) -> TrustedPrincipal:
        """Return the configured principal only for the configured test token."""
        if token != self.token:
            raise AuthenticationError
        return self.principal


def test_principal(
    *,
    principal_id: str = TEST_PRINCIPAL_ID,
    permissions: frozenset[Permission] = ALL_TEST_PERMISSIONS,
) -> TrustedPrincipal:
    """Return an explicit trusted test principal."""
    return TrustedPrincipal(principal_id=principal_id, permissions=permissions)


def create_authenticated_test_app(
    settings: Settings | None = None,
    product_inventory_repository: ProductInventoryRepository | None = None,
    recommendation_workflow_repository: RecommendationWorkflowRepository | None = None,
    clock: Clock | None = None,
    readiness_probe: ReadinessProbe | None = None,
    *,
    principal: TrustedPrincipal | None = None,
    token: str = TEST_BEARER_TOKEN,
) -> FastAPI:
    """Create an application with an explicitly injected test authenticator."""
    resolved_principal = principal if principal is not None else test_principal()
    return create_app(
        settings,
        product_inventory_repository,
        recommendation_workflow_repository,
        clock,
        readiness_probe,
        authenticator=StaticTestAuthenticator(resolved_principal, token),
    )


def authenticated_test_client(
    application: FastAPI,
    *,
    token: str = TEST_BEARER_TOKEN,
) -> TestClient:
    """Create a client that explicitly supplies one synthetic bearer token."""
    return TestClient(
        application,
        headers={"Authorization": f"Bearer {token}"},
    )
