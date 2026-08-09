"""API tests for stored reorder-recommendation review workflows."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import NoReturn, cast
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from opsmind.api.dependencies import get_product_inventory_repository
from opsmind.core.config import Environment, Settings
from opsmind.domain.errors import DuplicateRecommendationReviewError
from opsmind.domain.recommendation_review import ReorderRecommendationReview
from opsmind.repositories.in_memory_recommendation_workflow import (
    InMemoryRecommendationWorkflowRepository,
)
from opsmind.repositories.memory import InMemoryProductInventoryRepository
from tests.security import authenticated_test_client, create_authenticated_test_app

MISSING_ID = "00000000-0000-0000-0000-000000000099"
FIXED_TIME = datetime(2026, 8, 1, 17, 30, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class FixedClock:
    """Deterministic clock used by workflow API tests."""

    current: datetime = FIXED_TIME

    def now(self) -> datetime:
        """Return the fixed test instant."""
        return self.current


class TrackingWorkflowRepository(InMemoryRecommendationWorkflowRepository):
    """Count attempted review creations without exposing stored mappings."""

    def __init__(self) -> None:
        super().__init__()
        self.create_calls = 0

    def create_review(
        self,
        review: ReorderRecommendationReview,
        *,
        event_id: UUID,
    ) -> ReorderRecommendationReview:
        """Record and delegate a creation attempt."""
        self.create_calls += 1
        return super().create_review(review, event_id=event_id)


def make_settings(api_v1_prefix: str = "/api/v1") -> Settings:
    """Return deterministic review API settings."""
    return Settings(
        application_name="OpsMind Review Test",
        service_name="opsmind-review-test-api",
        environment=Environment.TEST,
        debug=False,
        api_v1_prefix=api_v1_prefix,
    )


def make_application(
    api_v1_prefix: str = "/api/v1",
) -> tuple[
    FastAPI,
    InMemoryProductInventoryRepository,
    InMemoryRecommendationWorkflowRepository,
]:
    """Build an isolated application with explicit repositories and clock."""
    product_repository = InMemoryProductInventoryRepository()
    workflow_repository = InMemoryRecommendationWorkflowRepository()
    application = create_authenticated_test_app(
        make_settings(api_v1_prefix),
        product_repository,
        workflow_repository,
        FixedClock(),
    )
    return application, product_repository, workflow_repository


def make_client(api_v1_prefix: str = "/api/v1") -> TestClient:
    """Return a client for one isolated review application."""
    application, _, _ = make_application(api_v1_prefix)
    return authenticated_test_client(application)


def create_product(
    client: TestClient,
    *,
    sku: str = "SENSOR-001",
    lead_time_days: int = 5,
    api_v1_prefix: str = "/api/v1",
) -> str:
    """Create one product and return its UUID."""
    response = client.post(
        f"{api_v1_prefix}/products",
        json={
            "sku": sku,
            "name": f"Product {sku}",
            "unit_of_measure": "units",
            "lead_time_days": lead_time_days,
        },
    )
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def set_inventory(
    client: TestClient,
    product_id: str,
    on_hand_quantity: int,
    allocated_quantity: int,
    *,
    api_v1_prefix: str = "/api/v1",
) -> None:
    """Set one product's inventory."""
    response = client.put(
        f"{api_v1_prefix}/products/{product_id}/inventory",
        json={
            "on_hand_quantity": on_hand_quantity,
            "allocated_quantity": allocated_quantity,
        },
    )
    assert response.status_code == 200


def add_demand(
    client: TestClient,
    product_id: str,
    *,
    api_v1_prefix: str = "/api/v1",
) -> None:
    """Store the standard four-day demand history."""
    response = client.post(
        f"{api_v1_prefix}/products/{product_id}/demand",
        json={
            "observations": [
                {"demand_date": "2026-07-01", "quantity": 12},
                {"demand_date": "2026-07-02", "quantity": 18},
                {"demand_date": "2026-07-03", "quantity": 9},
                {"demand_date": "2026-07-04", "quantity": 0},
            ]
        },
    )
    assert response.status_code == 201


def prepare_actionable_product(
    client: TestClient,
    *,
    api_v1_prefix: str = "/api/v1",
) -> str:
    """Create the issue's deterministic 19-unit recommendation inputs."""
    product_id = create_product(client, api_v1_prefix=api_v1_prefix)
    set_inventory(
        client,
        product_id,
        40,
        10,
        api_v1_prefix=api_v1_prefix,
    )
    add_demand(client, product_id, api_v1_prefix=api_v1_prefix)
    return product_id


def create_review(
    client: TestClient,
    product_id: str,
    *,
    api_v1_prefix: str = "/api/v1",
) -> dict[str, object]:
    """Create and return one standard stored recommendation review."""
    response = client.post(
        f"{api_v1_prefix}/products/{product_id}/reorder-recommendations"
        "?lookback_observations=4&as_of_date=2026-07-04"
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def get_audit_history(
    client: TestClient,
    recommendation_id: object,
    *,
    api_v1_prefix: str = "/api/v1",
) -> dict[str, object]:
    """Retrieve one stored recommendation's audit history."""
    response = client.get(
        f"{api_v1_prefix}/reorder-recommendations/{recommendation_id}/audit-events"
    )
    assert response.status_code == 200
    return cast(dict[str, object], response.json())


def test_create_review_returns_pending_immutable_recommendation_snapshot() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)

    response = client.post(
        f"/api/v1/products/{product_id}/reorder-recommendations"
        "?lookback_observations=4&as_of_date=2026-07-04"
    )

    assert response.status_code == 201
    body = response.json()
    UUID(body["recommendation_id"])
    assert body["review_status"] == "pending_review"
    assert body["created_at"] == "2026-08-01T17:30:00Z"
    assert body["decision"] is None
    assert body["recommendation"] == {
        "product_id": product_id,
        "unit_of_measure": "units",
        "recommendation_policy": "projected_shortage_ceiling",
        "recommendation_status": "reorder_recommended",
        "forecast_method": "simple_mean",
        "as_of_date": "2026-07-04",
        "lookback_observations_requested": 4,
        "observations_used": 4,
        "training_start_date": "2026-07-01",
        "training_end_date": "2026-07-04",
        "average_daily_demand": 9.75,
        "lead_time_days": 5,
        "on_hand_quantity": 40,
        "allocated_quantity": 10,
        "available_inventory": 30,
        "forecasted_lead_time_demand": 48.75,
        "projected_inventory_balance": -18.75,
        "projected_shortage_quantity": 18.75,
        "recommended_reorder_quantity": 19,
    }


def test_pending_review_history_contains_one_creation_event() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)

    history = get_audit_history(client, created["recommendation_id"])

    assert history["recommendation_id"] == created["recommendation_id"]
    events = cast(list[dict[str, object]], history["events"])
    assert len(events) == 1
    event = events[0]
    UUID(cast(str, event["event_id"]))
    assert event == {
        "event_id": event["event_id"],
        "recommendation_id": created["recommendation_id"],
        "sequence_number": 1,
        "event_type": "review_created",
        "occurred_at": created["created_at"],
        "review_status": "pending_review",
        "decision_id": None,
        "actor": None,
        "recommended_reorder_quantity": 19,
        "approved_quantity": None,
        "note": None,
    }


def test_approved_history_links_original_snapshot_and_decision() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)
    recommendation_id = created["recommendation_id"]
    approved = client.post(
        f"/api/v1/reorder-recommendations/{recommendation_id}/approve",
        json={
            "approved_quantity": 24,
            "note": " Case pack ",
        },
    ).json()

    history = get_audit_history(client, recommendation_id)
    events = cast(list[dict[str, object]], history["events"])

    assert [event["sequence_number"] for event in events] == [1, 2]
    assert [event["event_type"] for event in events] == [
        "review_created",
        "recommendation_approved",
    ]
    terminal = events[1]
    assert terminal["review_status"] == "approved"
    assert terminal["decision_id"] == approved["decision"]["decision_id"]
    assert terminal["actor"] == "Reviewer"
    assert terminal["recommended_reorder_quantity"] == 19
    assert terminal["approved_quantity"] == 24
    assert terminal["note"] == "Case pack"
    assert terminal["occurred_at"] == approved["decision"]["decided_at"]


def test_rejected_history_links_reason_and_decision() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)
    recommendation_id = created["recommendation_id"]
    rejected = client.post(
        f"/api/v1/reorder-recommendations/{recommendation_id}/reject",
        json={"reason": " Inbound scheduled. "},
    ).json()

    history = get_audit_history(client, recommendation_id)
    events = cast(list[dict[str, object]], history["events"])
    terminal = events[1]

    assert [event["event_type"] for event in events] == [
        "review_created",
        "recommendation_rejected",
    ]
    assert terminal["review_status"] == "rejected"
    assert terminal["decision_id"] == rejected["decision"]["decision_id"]
    assert terminal["actor"] == "Reviewer"
    assert terminal["approved_quantity"] is None
    assert terminal["note"] == "Inbound scheduled."
    assert terminal["occurred_at"] == rejected["decision"]["decided_at"]


def test_default_creation_parameters_use_latest_eligible_history() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)

    response = client.post(f"/api/v1/products/{product_id}/reorder-recommendations")

    assert response.status_code == 201
    recommendation = response.json()["recommendation"]
    assert recommendation["lookback_observations_requested"] == 7
    assert recommendation["as_of_date"] == "2026-07-04"


def test_stored_snapshot_does_not_recalculate_after_inventory_change() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)
    recommendation_id = created["recommendation_id"]

    set_inventory(client, product_id, 100, 0)
    calculated = client.get(
        f"/api/v1/products/{product_id}/reorder-recommendation"
        "?lookback_observations=4&as_of_date=2026-07-04"
    )
    retrieved = client.get(f"/api/v1/reorder-recommendations/{recommendation_id}")

    assert calculated.status_code == 200
    assert calculated.json()["recommended_reorder_quantity"] == 0
    assert retrieved.status_code == 200
    assert retrieved.json() == created
    assert retrieved.json()["recommendation"]["recommended_reorder_quantity"] == 19
    assert retrieved.json()["recommendation"]["on_hand_quantity"] == 40


def test_retrieval_uses_only_workflow_repository() -> None:
    application, _, _ = make_application()
    client = authenticated_test_client(application)
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)

    def fail_product_repository() -> NoReturn:
        raise AssertionError("retrieval must not access operational repository")

    application.dependency_overrides[get_product_inventory_repository] = (
        fail_product_repository
    )

    response = client.get(
        f"/api/v1/reorder-recommendations/{created['recommendation_id']}"
    )

    assert response.status_code == 200
    assert response.json() == created


def test_multiple_creations_store_separate_snapshots() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)

    first = create_review(client, product_id)
    second = create_review(client, product_id)

    assert first["recommendation_id"] != second["recommendation_id"]
    assert first["recommendation"] == second["recommendation"]


def test_no_actionable_recommendation_returns_safe_409_and_stores_nothing() -> None:
    product_repository = InMemoryProductInventoryRepository()
    workflow_repository = TrackingWorkflowRepository()
    application = create_authenticated_test_app(
        make_settings(),
        product_repository,
        workflow_repository,
        FixedClock(),
    )
    client = authenticated_test_client(application)
    product_id = create_product(client)
    set_inventory(client, product_id, 100, 0)
    add_demand(client, product_id)

    response = client.post(f"/api/v1/products/{product_id}/reorder-recommendations")

    assert response.status_code == 409
    assert response.json() == {
        "detail": f"Product '{product_id}' has no actionable reorder recommendation."
    }
    assert workflow_repository.create_calls == 0


@pytest.mark.parametrize(
    ("setup", "expected_status"),
    [("missing_product", 404), ("missing_inventory", 404), ("missing_demand", 422)],
)
def test_creation_preserves_existing_input_error_contracts(
    setup: str,
    expected_status: int,
) -> None:
    client = make_client()
    product_id = MISSING_ID
    if setup != "missing_product":
        product_id = create_product(client)
    if setup == "missing_demand":
        set_inventory(client, product_id, 10, 0)

    response = client.post(f"/api/v1/products/{product_id}/reorder-recommendations")

    assert response.status_code == expected_status


@pytest.mark.parametrize(
    "suffix",
    [
        "?lookback_observations=0",
        "?lookback_observations=366",
        "?as_of_date=not-a-date",
    ],
)
def test_creation_rejects_invalid_query_values(suffix: str) -> None:
    response = make_client().post(
        f"/api/v1/products/{MISSING_ID}/reorder-recommendations{suffix}"
    )

    assert response.status_code == 422


def test_retrieval_returns_safe_404_and_invalid_uuid_returns_422() -> None:
    client = make_client()

    missing = client.get(f"/api/v1/reorder-recommendations/{MISSING_ID}")
    invalid = client.get("/api/v1/reorder-recommendations/not-a-uuid")

    assert missing.status_code == 404
    assert missing.json() == {
        "detail": f"Reorder recommendation '{MISSING_ID}' was not found."
    }
    assert invalid.status_code == 422


def test_audit_history_returns_safe_404_and_invalid_uuid_returns_422() -> None:
    client = make_client()

    missing = client.get(f"/api/v1/reorder-recommendations/{MISSING_ID}/audit-events")
    invalid = client.get("/api/v1/reorder-recommendations/not-a-uuid/audit-events")

    assert missing.status_code == 404
    assert missing.json() == {
        "detail": f"Reorder recommendation '{MISSING_ID}' was not found."
    }
    assert invalid.status_code == 422


def test_approval_defaults_quantity_and_uses_trusted_actor() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)

    response = client.post(
        f"/api/v1/reorder-recommendations/{created['recommendation_id']}/approve",
        json={"note": " Approved as recommended. "},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["review_status"] == "approved"
    assert body["recommendation"] == created["recommendation"]
    assert body["decision"]["decision_type"] == "approved"
    assert body["decision"]["decided_by"] == "Reviewer"
    assert body["decision"]["decided_at"] == "2026-08-01T17:30:00Z"
    assert body["decision"]["approved_quantity"] == 19
    assert body["decision"]["note"] == "Approved as recommended."


def test_approval_preserves_distinct_approved_quantity() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)

    response = client.post(
        f"/api/v1/reorder-recommendations/{created['recommendation_id']}/approve",
        json={
            "approved_quantity": 24,
            "note": "Case pack of six",
        },
    )

    assert response.status_code == 200
    assert response.json()["recommendation"]["recommended_reorder_quantity"] == 19
    assert response.json()["decision"]["approved_quantity"] == 24


def test_identical_approval_retry_preserves_original_decision() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)
    path = f"/api/v1/reorder-recommendations/{created['recommendation_id']}/approve"

    first = client.post(
        path,
        json={"approved_quantity": 19, "note": "Ok"},
    )
    retry = client.post(
        path,
        json={"note": " Ok "},
    )

    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert (
        retry.json()["decision"]["decision_id"]
        == first.json()["decision"]["decision_id"]
    )
    assert (
        retry.json()["decision"]["decided_at"] == first.json()["decision"]["decided_at"]
    )
    first_history = get_audit_history(client, created["recommendation_id"])
    second_history = get_audit_history(client, created["recommendation_id"])
    assert first_history == second_history
    assert len(cast(list[object], first_history["events"])) == 2


@pytest.mark.parametrize(
    "changed_request",
    [
        {"approved_quantity": 20, "note": "Ok"},
        {"approved_quantity": 19, "note": "Different"},
    ],
)
def test_changed_approval_retry_returns_409_and_preserves_state(
    changed_request: dict[str, object],
) -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)
    recommendation_id = created["recommendation_id"]
    path = f"/api/v1/reorder-recommendations/{recommendation_id}/approve"
    approved = client.post(
        path,
        json={"approved_quantity": 19, "note": "Ok"},
    ).json()
    history_before = get_audit_history(client, recommendation_id)

    conflict = client.post(path, json=changed_request)
    stored = client.get(f"/api/v1/reorder-recommendations/{recommendation_id}")
    history_after = get_audit_history(client, recommendation_id)

    assert conflict.status_code == 409
    assert stored.json() == approved
    assert history_after == history_before


def test_rejection_records_reason_and_identical_retry_is_stable() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)
    path = f"/api/v1/reorder-recommendations/{created['recommendation_id']}/reject"

    first = client.post(
        path,
        json={"reason": " Inbound scheduled. "},
    )
    retry = client.post(
        path,
        json={"reason": "Inbound scheduled."},
    )

    assert first.status_code == retry.status_code == 200
    assert retry.json() == first.json()
    assert first.json()["review_status"] == "rejected"
    assert first.json()["decision"]["decision_type"] == "rejected"
    assert first.json()["decision"]["approved_quantity"] is None
    assert first.json()["decision"]["note"] == "Inbound scheduled."
    history = get_audit_history(client, created["recommendation_id"])
    assert len(cast(list[object], history["events"])) == 2


def test_changed_rejection_and_cross_decision_requests_conflict() -> None:
    client = make_client()
    approved_product = prepare_actionable_product(client)
    approved = create_review(client, approved_product)
    rejected_product = create_product(client, sku="SENSOR-002")
    set_inventory(client, rejected_product, 40, 10)
    add_demand(client, rejected_product)
    rejected = create_review(client, rejected_product)
    approved_id = approved["recommendation_id"]
    rejected_id = rejected["recommendation_id"]
    client.post(
        f"/api/v1/reorder-recommendations/{approved_id}/approve",
        json={},
    )
    client.post(
        f"/api/v1/reorder-recommendations/{rejected_id}/reject",
        json={"reason": "Inbound"},
    )
    approved_history = get_audit_history(client, approved_id)
    rejected_history = get_audit_history(client, rejected_id)

    assert (
        client.post(
            f"/api/v1/reorder-recommendations/{approved_id}/reject",
            json={"reason": "Inbound"},
        ).status_code
        == 409
    )
    assert get_audit_history(client, approved_id) == approved_history
    assert get_audit_history(client, rejected_id) == rejected_history
    assert (
        client.post(
            f"/api/v1/reorder-recommendations/{rejected_id}/approve",
            json={},
        ).status_code
        == 409
    )
    assert (
        client.post(
            f"/api/v1/reorder-recommendations/{rejected_id}/reject",
            json={"reason": "Different"},
        ).status_code
        == 409
    )
    assert get_audit_history(client, approved_id) == approved_history
    assert get_audit_history(client, rejected_id) == rejected_history


@pytest.mark.parametrize(
    ("operation", "payload"),
    [
        ("approve", {"decided_by": "caller-controlled"}),
        ("approve", {"approved_quantity": 0}),
        ("approve", {"approved_quantity": 1.5}),
        ("approve", {"approved_quantity": True}),
        ("reject", {"decided_by": "caller-controlled", "reason": "No"}),
        ("reject", {"reason": " "}),
    ],
)
def test_decision_request_validation_returns_422(
    operation: str,
    payload: dict[str, object],
) -> None:
    response = make_client().post(
        f"/api/v1/reorder-recommendations/{MISSING_ID}/{operation}",
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("operation", ["approve", "reject"])
def test_decision_for_missing_review_returns_404(operation: str) -> None:
    payload = {} if operation == "approve" else {"reason": "No"}

    response = make_client().post(
        f"/api/v1/reorder-recommendations/{MISSING_ID}/{operation}",
        json=payload,
    )

    assert response.status_code == 404


def test_decisions_use_only_workflow_repository_after_snapshot_creation() -> None:
    application, _, _ = make_application()
    client = authenticated_test_client(application)
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)

    def fail_product_repository() -> NoReturn:
        raise AssertionError("decisions must not access operational repository")

    application.dependency_overrides[get_product_inventory_repository] = (
        fail_product_repository
    )

    response = client.post(
        f"/api/v1/reorder-recommendations/{created['recommendation_id']}/approve",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["review_status"] == "approved"


def test_audit_retrieval_is_read_only_and_uses_only_workflow_repository() -> None:
    application, _, _ = make_application()
    client = authenticated_test_client(application)
    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)
    recommendation_id = created["recommendation_id"]
    review_before = client.get(
        f"/api/v1/reorder-recommendations/{recommendation_id}"
    ).json()
    history_before = get_audit_history(client, recommendation_id)

    set_inventory(client, product_id, 100, 0)
    demand_response = client.post(
        f"/api/v1/products/{product_id}/demand",
        json={"observations": [{"demand_date": "2026-07-05", "quantity": 99}]},
    )
    assert demand_response.status_code == 201

    def fail_product_repository() -> NoReturn:
        raise AssertionError("audit retrieval must not access operational data")

    application.dependency_overrides[get_product_inventory_repository] = (
        fail_product_repository
    )

    first = get_audit_history(client, recommendation_id)
    second = get_audit_history(client, recommendation_id)
    review_after = client.get(
        f"/api/v1/reorder-recommendations/{recommendation_id}"
    ).json()

    assert first == second == history_before
    assert review_after == review_before


def test_default_applications_isolate_workflow_state() -> None:
    first = make_client()
    second = make_client()
    product_id = prepare_actionable_product(first)
    created = create_review(first, product_id)

    assert (
        first.get(
            f"/api/v1/reorder-recommendations/{created['recommendation_id']}"
        ).status_code
        == 200
    )
    assert (
        second.get(
            f"/api/v1/reorder-recommendations/{created['recommendation_id']}"
        ).status_code
        == 404
    )
    assert (
        second.get(
            f"/api/v1/reorder-recommendations/"
            f"{created['recommendation_id']}/audit-events"
        ).status_code
        == 404
    )


def test_shared_workflow_repository_exposes_shared_history_deliberately() -> None:
    shared = InMemoryRecommendationWorkflowRepository()
    first_product_repository = InMemoryProductInventoryRepository()
    first = authenticated_test_client(
        create_authenticated_test_app(
            make_settings(),
            first_product_repository,
            shared,
            FixedClock(),
        )
    )
    second = authenticated_test_client(
        create_authenticated_test_app(
            make_settings(),
            InMemoryProductInventoryRepository(),
            shared,
            FixedClock(),
        )
    )
    product_id = prepare_actionable_product(first)
    created = create_review(first, product_id)

    assert get_audit_history(second, created["recommendation_id"]) == (
        get_audit_history(first, created["recommendation_id"])
    )


def test_custom_prefix_applies_and_health_remains_exact_and_unversioned() -> None:
    prefix = "/supply/v2"
    client = make_client(prefix)
    product_id = prepare_actionable_product(client, api_v1_prefix=prefix)

    created = create_review(client, product_id, api_v1_prefix=prefix)

    assert (
        client.get(
            f"{prefix}/reorder-recommendations/{created['recommendation_id']}"
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/v1/reorder-recommendations/{created['recommendation_id']}"
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"{prefix}/reorder-recommendations/"
            f"{created['recommendation_id']}/audit-events"
        ).status_code
        == 200
    )
    assert client.get("/health").json() == {
        "status": "ok",
        "service": "opsmind-review-test-api",
        "environment": "test",
    }
    assert client.get(f"{prefix}/health").status_code == 404


def test_review_workflow_does_not_create_orders_or_mutate_operational_state() -> None:
    client = make_client()
    product_id = prepare_actionable_product(client)
    product_before = client.get(f"/api/v1/products/{product_id}").json()
    inventory_before = client.get(f"/api/v1/products/{product_id}/inventory").json()
    demand_before = client.get(f"/api/v1/products/{product_id}/demand").json()
    created = create_review(client, product_id)
    client.post(
        f"/api/v1/reorder-recommendations/{created['recommendation_id']}/approve",
        json={},
    )

    assert client.get(f"/api/v1/products/{product_id}").json() == product_before
    assert (
        client.get(f"/api/v1/products/{product_id}/inventory").json()
        == inventory_before
    )
    assert client.get(f"/api/v1/products/{product_id}/demand").json() == demand_before
    assert client.get("/api/v1/orders").status_code == 404


def test_openapi_documents_review_contract_and_bounded_responses() -> None:
    schema = make_client().get("/openapi.json").json()
    paths = schema["paths"]
    create_operation = paths["/api/v1/products/{product_id}/reorder-recommendations"][
        "post"
    ]
    get_operation = paths["/api/v1/reorder-recommendations/{recommendation_id}"]["get"]
    approve_operation = paths[
        "/api/v1/reorder-recommendations/{recommendation_id}/approve"
    ]["post"]
    reject_operation = paths[
        "/api/v1/reorder-recommendations/{recommendation_id}/reject"
    ]["post"]
    audit_path = paths[
        "/api/v1/reorder-recommendations/{recommendation_id}/audit-events"
    ]
    audit_operation = audit_path["get"]

    assert set(create_operation["responses"]) >= {"201", "404", "409", "422"}
    assert set(get_operation["responses"]) >= {"200", "404", "422"}
    assert set(approve_operation["responses"]) >= {"200", "404", "409", "422"}
    assert set(reject_operation["responses"]) >= {"200", "404", "409", "422"}
    assert set(audit_operation["responses"]) >= {"200", "404", "422"}
    assert set(audit_path) == {"get"}
    assert audit_operation["parameters"][0]["schema"]["format"] == "uuid"
    assert schema["components"]["schemas"]["RecommendationReviewStatus"]["enum"] == [
        "pending_review",
        "approved",
        "rejected",
    ]
    assert schema["components"]["schemas"]["RecommendationDecisionType"]["enum"] == [
        "approved",
        "rejected",
    ]
    assert schema["components"]["schemas"]["RecommendationAuditEventType"]["enum"] == [
        "review_created",
        "recommendation_approved",
        "recommendation_rejected",
    ]
    review_properties = schema["components"]["schemas"][
        "ReorderRecommendationReviewResponse"
    ]["properties"]
    assert set(review_properties) == {
        "recommendation_id",
        "recommendation",
        "review_status",
        "created_at",
        "decision",
    }
    decision_properties = schema["components"]["schemas"][
        "RecommendationDecisionResponse"
    ]["properties"]
    assert set(decision_properties) == {
        "decision_id",
        "decision_type",
        "decided_by",
        "decided_at",
        "approved_quantity",
        "note",
    }
    forbidden_fields = {
        "purchase_order_id",
        "supplier",
        "authentication",
        "authorized_by",
        "audit_events",
        "correlation_id",
    }
    assert forbidden_fields.isdisjoint(review_properties | decision_properties)
    history_properties = schema["components"]["schemas"][
        "RecommendationAuditHistoryResponse"
    ]["properties"]
    event_properties = schema["components"]["schemas"][
        "RecommendationAuditEventResponse"
    ]["properties"]
    assert set(history_properties) == {"recommendation_id", "events"}
    assert set(event_properties) == {
        "event_id",
        "recommendation_id",
        "sequence_number",
        "event_type",
        "occurred_at",
        "review_status",
        "decision_id",
        "actor",
        "recommended_reorder_quantity",
        "approved_quantity",
        "note",
    }
    assert event_properties["occurred_at"]["format"] == "date-time"
    assert event_properties["sequence_number"]["type"] == "integer"
    assert event_properties["recommended_reorder_quantity"]["type"] == "integer"
    assert {
        choice.get("type") for choice in event_properties["decision_id"]["anyOf"]
    } == {
        "string",
        "null",
    }


def test_duplicate_creation_repository_error_returns_safe_409(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Repository recommendation-ID collisions retain the 409 contract."""
    product_repository = InMemoryProductInventoryRepository()
    workflow_repository = InMemoryRecommendationWorkflowRepository()

    application = create_authenticated_test_app(
        make_settings(),
        product_repository,
        workflow_repository,
        FixedClock(),
    )
    client = authenticated_test_client(application)
    product_id = prepare_actionable_product(client)

    attempted_ids: list[UUID] = []

    def fail_create(
        review: ReorderRecommendationReview,
        *,
        event_id: UUID,
    ) -> NoReturn:
        del event_id
        attempted_ids.append(review.recommendation_id)
        raise DuplicateRecommendationReviewError(review.recommendation_id)

    monkeypatch.setattr(
        workflow_repository,
        "create_review",
        fail_create,
    )

    response = client.post(f"/api/v1/products/{product_id}/reorder-recommendations")

    assert response.status_code == 409
    assert len(attempted_ids) == 1
    assert response.json() == {
        "detail": (f"Reorder recommendation '{attempted_ids[0]}' already exists.")
    }


@pytest.mark.parametrize(
    ("operation", "payload"),
    [
        ("approve", {}),
        (
            "reject",
            {
                "reason": "Do not replenish",
            },
        ),
    ],
)
def test_repository_value_error_during_decision_returns_safe_422(
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    payload: dict[str, object],
) -> None:
    """Repository value failures remain bounded as public 422s."""
    application, _, workflow_repository = make_application()
    client = authenticated_test_client(application)

    product_id = prepare_actionable_product(client)
    created = create_review(client, product_id)
    recommendation_id = cast(
        str,
        created["recommendation_id"],
    )

    def fail_decision(
        *args: object,
        **kwargs: object,
    ) -> NoReturn:
        del args, kwargs
        raise ValueError("synthetic invalid terminal decision")

    monkeypatch.setattr(
        workflow_repository,
        f"{operation}_review",
        fail_decision,
    )

    response = client.post(
        (f"/api/v1/reorder-recommendations/{recommendation_id}/{operation}"),
        json=payload,
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "synthetic invalid terminal decision"}
