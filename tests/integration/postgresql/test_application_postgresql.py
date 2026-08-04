"""PostgreSQL-backed application sharing, durability, and analytical tests."""

from typing import cast
from uuid import UUID

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.engine import URL

from opsmind.application import create_app
from opsmind.core.config import Environment, PersistenceBackend, Settings
from opsmind.persistence.postgresql.database import SessionFactory
from opsmind.persistence.postgresql.models import (
    RecommendationAuditEventRow,
    RecommendationDecisionRow,
    RecommendationReviewRow,
)


def postgresql_settings(
    postgresql_url: URL,
    *,
    api_v1_prefix: str = "/api/v1",
) -> Settings:
    """Create test settings without rendering the URL in assertions or output."""
    return Settings(
        application_name="OpsMind PostgreSQL Test",
        service_name="opsmind-postgresql-test",
        environment=Environment.TEST,
        api_v1_prefix=api_v1_prefix,
        persistence_backend=PersistenceBackend.POSTGRESQL,
        database_url=SecretStr(postgresql_url.render_as_string(hide_password=False)),
    )


def create_product(client: TestClient, *, prefix: str = "/api/v1") -> str:
    response = client.post(
        f"{prefix}/products",
        json={
            "sku": "SENSOR-001",
            "name": "Temperature Sensor",
            "unit_of_measure": "units",
            "lead_time_days": 5,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return str(response.json()["id"])


def seed_operational_flow(client: TestClient, product_id: str) -> None:
    inventory_response = client.put(
        f"/api/v1/products/{product_id}/inventory",
        json={"on_hand_quantity": 40, "allocated_quantity": 10},
    )
    demand_response = client.post(
        f"/api/v1/products/{product_id}/demand",
        json={
            "observations": [
                {"demand_date": "2026-07-01", "quantity": 12},
                {"demand_date": "2026-07-02", "quantity": 18},
                {"demand_date": "2026-07-03", "quantity": 9},
                {"demand_date": "2026-07-04", "quantity": 0},
                {"demand_date": "2026-07-10", "quantity": 21},
            ]
        },
    )
    assert inventory_response.status_code == 200
    assert demand_response.status_code == 201


def assert_analytical_flow(client: TestClient, product_id: str) -> None:
    query = "?lookback_observations=4&as_of_date=2026-07-04"
    forecast = client.get(
        f"/api/v1/products/{product_id}/forecast{query}&horizon_days=7"
    )
    exposure = client.get(f"/api/v1/products/{product_id}/stockout-exposure{query}")
    reorder = client.get(f"/api/v1/products/{product_id}/reorder-recommendation{query}")

    assert forecast.status_code == 200
    assert forecast.json()["average_daily_demand"] == 9.75
    assert forecast.json()["forecast_quantity"] == 68.25
    assert exposure.status_code == 200
    assert exposure.json()["projected_shortage_quantity"] == 18.75
    assert reorder.status_code == 200
    assert reorder.json()["recommended_reorder_quantity"] == 19


def create_workflow_review(
    client: TestClient,
    product_id: str,
) -> dict[str, object]:
    """Create one actionable stored workflow through the public API."""
    response = client.post(
        f"/api/v1/products/{product_id}/reorder-recommendations",
        params={
            "lookback_observations": 4,
            "as_of_date": "2026-07-04",
        },
    )
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def get_workflow_review(
    client: TestClient,
    recommendation_id: str,
) -> dict[str, object]:
    """Retrieve one stored workflow through the public API."""
    response = client.get(f"/api/v1/reorder-recommendations/{recommendation_id}")
    assert response.status_code == 200
    return cast(dict[str, object], response.json())


def get_workflow_history(
    client: TestClient,
    recommendation_id: str,
) -> dict[str, object]:
    """Retrieve one sequence-ordered workflow history."""
    response = client.get(
        f"/api/v1/reorder-recommendations/{recommendation_id}/audit-events"
    )
    assert response.status_code == 200
    return cast(dict[str, object], response.json())


def assert_workflow_row_counts(
    session_factory: SessionFactory,
    recommendation_id: str,
    *,
    decisions: int,
    events: int,
) -> None:
    """Verify retry behavior against persisted workflow row counts."""
    workflow_id = UUID(recommendation_id)

    with session_factory() as session:
        review_count = session.scalar(
            select(func.count())
            .select_from(RecommendationReviewRow)
            .where(RecommendationReviewRow.recommendation_id == workflow_id)
        )
        decision_count = session.scalar(
            select(func.count())
            .select_from(RecommendationDecisionRow)
            .where(RecommendationDecisionRow.recommendation_id == workflow_id)
        )
        event_count = session.scalar(
            select(func.count())
            .select_from(RecommendationAuditEventRow)
            .where(RecommendationAuditEventRow.recommendation_id == workflow_id)
        )

    assert review_count == 1
    assert decision_count == decisions
    assert event_count == events


def test_shared_operational_and_approved_workflow_state_survive_restarts(
    postgresql_url: URL,
    session_factory: SessionFactory,
) -> None:
    settings = postgresql_settings(postgresql_url)

    with TestClient(create_app(settings)) as first_client:
        product_id = create_product(first_client)
        seed_operational_flow(first_client, product_id)
        assert_analytical_flow(first_client, product_id)

        created = create_workflow_review(first_client, product_id)
        recommendation_id = str(created["recommendation_id"])
        pending_history = get_workflow_history(
            first_client,
            recommendation_id,
        )
        pending_events = cast(
            list[dict[str, object]],
            pending_history["events"],
        )

        assert created["review_status"] == "pending_review"
        assert created["decision"] is None
        assert [event["sequence_number"] for event in pending_events] == [1]
        assert [event["event_type"] for event in pending_events] == ["review_created"]

        with TestClient(create_app(settings)) as second_client:
            assert (
                second_client.get(f"/api/v1/products/{product_id}").status_code == 200
            )
            assert_analytical_flow(second_client, product_id)
            assert (
                get_workflow_review(
                    second_client,
                    recommendation_id,
                )
                == created
            )
            assert (
                get_workflow_history(
                    second_client,
                    recommendation_id,
                )
                == pending_history
            )

            second_product = second_client.post(
                "/api/v1/products",
                json={
                    "sku": "ACTUATOR-001",
                    "name": "Actuator",
                    "unit_of_measure": "units",
                    "lead_time_days": 2,
                },
            )
            assert second_product.status_code == 201
            assert len(first_client.get("/api/v1/products").json()) == 2

    assert_workflow_row_counts(
        session_factory,
        recommendation_id,
        decisions=0,
        events=1,
    )

    approval_path = f"/api/v1/reorder-recommendations/{recommendation_id}/approve"
    approval_request = {
        "decided_by": "Reviewer",
        "approved_quantity": 19,
        "note": "Ok",
    }

    with TestClient(create_app(settings)) as restarted_client:
        assert restarted_client.get(f"/api/v1/products/{product_id}").status_code == 200
        assert (
            len(restarted_client.get(f"/api/v1/products/{product_id}/demand").json())
            == 5
        )
        assert (
            get_workflow_review(
                restarted_client,
                recommendation_id,
            )
            == created
        )
        assert_analytical_flow(restarted_client, product_id)

        approval_response = restarted_client.post(
            approval_path,
            json=approval_request,
        )
        assert approval_response.status_code == 200
        approved = cast(
            dict[str, object],
            approval_response.json(),
        )
        approved_history = get_workflow_history(
            restarted_client,
            recommendation_id,
        )
        approved_events = cast(
            list[dict[str, object]],
            approved_history["events"],
        )

        assert approved["review_status"] == "approved"
        assert approved["recommendation"] == created["recommendation"]
        decision = cast(dict[str, object], approved["decision"])
        assert decision["decision_type"] == "approved"
        assert decision["decided_by"] == "Reviewer"
        assert decision["approved_quantity"] == 19
        assert decision["note"] == "Ok"
        assert [event["sequence_number"] for event in approved_events] == [
            1,
            2,
        ]
        assert [event["event_type"] for event in approved_events] == [
            "review_created",
            "recommendation_approved",
        ]

    assert_workflow_row_counts(
        session_factory,
        recommendation_id,
        decisions=1,
        events=2,
    )

    with TestClient(create_app(settings)) as final_client:
        assert get_workflow_review(final_client, recommendation_id) == approved
        assert get_workflow_history(final_client, recommendation_id) == approved_history

        retry = final_client.post(
            approval_path,
            json={
                "decided_by": " Reviewer ",
                "note": " Ok ",
            },
        )
        assert retry.status_code == 200
        assert retry.json() == approved
        assert get_workflow_history(final_client, recommendation_id) == approved_history

        changed = final_client.post(
            approval_path,
            json={
                "decided_by": "Reviewer",
                "approved_quantity": 20,
                "note": "Ok",
            },
        )
        opposite = final_client.post(
            f"/api/v1/reorder-recommendations/{recommendation_id}/reject",
            json={
                "decided_by": "Reviewer",
                "reason": "Inbound",
            },
        )

        assert changed.status_code == 409
        assert opposite.status_code == 409
        for conflict in (changed, opposite):
            assert "sql" not in conflict.text.lower()
            assert "constraint" not in conflict.text.lower()
            assert "postgres" not in conflict.text.lower()

        assert get_workflow_review(final_client, recommendation_id) == approved
        assert get_workflow_history(final_client, recommendation_id) == approved_history

    assert_workflow_row_counts(
        session_factory,
        recommendation_id,
        decisions=1,
        events=2,
    )


def test_rejected_workflow_survives_restart_and_retries_idempotently(
    postgresql_url: URL,
    session_factory: SessionFactory,
) -> None:
    settings = postgresql_settings(postgresql_url)

    with TestClient(create_app(settings)) as creation_client:
        product_id = create_product(creation_client)
        seed_operational_flow(creation_client, product_id)
        created = create_workflow_review(
            creation_client,
            product_id,
        )
        recommendation_id = str(created["recommendation_id"])

    rejection_path = f"/api/v1/reorder-recommendations/{recommendation_id}/reject"

    with TestClient(create_app(settings)) as decision_client:
        assert (
            get_workflow_review(
                decision_client,
                recommendation_id,
            )
            == created
        )

        response = decision_client.post(
            rejection_path,
            json={
                "decided_by": " Reviewer ",
                "reason": " Inbound scheduled. ",
            },
        )
        assert response.status_code == 200
        rejected = cast(dict[str, object], response.json())
        rejected_history = get_workflow_history(
            decision_client,
            recommendation_id,
        )
        rejected_events = cast(
            list[dict[str, object]],
            rejected_history["events"],
        )

        assert rejected["review_status"] == "rejected"
        decision = cast(dict[str, object], rejected["decision"])
        assert decision["decision_type"] == "rejected"
        assert decision["decided_by"] == "Reviewer"
        assert decision["approved_quantity"] is None
        assert decision["note"] == "Inbound scheduled."
        assert [event["sequence_number"] for event in rejected_events] == [
            1,
            2,
        ]
        assert [event["event_type"] for event in rejected_events] == [
            "review_created",
            "recommendation_rejected",
        ]

    assert_workflow_row_counts(
        session_factory,
        recommendation_id,
        decisions=1,
        events=2,
    )

    with TestClient(create_app(settings)) as restarted_client:
        assert (
            get_workflow_review(
                restarted_client,
                recommendation_id,
            )
            == rejected
        )
        assert (
            get_workflow_history(
                restarted_client,
                recommendation_id,
            )
            == rejected_history
        )

        retry = restarted_client.post(
            rejection_path,
            json={
                "decided_by": "Reviewer",
                "reason": "Inbound scheduled.",
            },
        )
        changed = restarted_client.post(
            rejection_path,
            json={
                "decided_by": "Reviewer",
                "reason": "Different",
            },
        )
        opposite = restarted_client.post(
            f"/api/v1/reorder-recommendations/{recommendation_id}/approve",
            json={"decided_by": "Reviewer"},
        )

        assert retry.status_code == 200
        assert retry.json() == rejected
        assert changed.status_code == 409
        assert opposite.status_code == 409
        assert (
            get_workflow_review(
                restarted_client,
                recommendation_id,
            )
            == rejected
        )
        assert (
            get_workflow_history(
                restarted_client,
                recommendation_id,
            )
            == rejected_history
        )

    assert_workflow_row_counts(
        session_factory,
        recommendation_id,
        decisions=1,
        events=2,
    )


def test_postgresql_api_preserves_safe_conflicts_and_batch_atomicity(
    postgresql_url: URL,
    clean_postgresql: None,
) -> None:
    with TestClient(create_app(postgresql_settings(postgresql_url))) as client:
        product_id = create_product(client)
        duplicate = client.post(
            "/api/v1/products",
            json={
                "sku": " sensor-001 ",
                "name": "Duplicate",
                "unit_of_measure": "units",
                "lead_time_days": 1,
            },
        )
        assert duplicate.status_code == 409
        assert duplicate.json() == {
            "detail": "A product with SKU 'SENSOR-001' already exists."
        }

        demand_path = f"/api/v1/products/{product_id}/demand"
        assert (
            client.post(
                demand_path,
                json={"observations": [{"demand_date": "2026-07-01", "quantity": 12}]},
            ).status_code
            == 201
        )
        conflict = client.post(
            demand_path,
            json={
                "observations": [
                    {"demand_date": "2026-07-02", "quantity": 18},
                    {"demand_date": "2026-07-01", "quantity": 99},
                ]
            },
        )
        assert conflict.status_code == 409
        assert [item["demand_date"] for item in client.get(demand_path).json()] == [
            "2026-07-01"
        ]
        assert "sql" not in conflict.text.lower()
        assert "constraint" not in conflict.text.lower()
        assert "postgres" not in conflict.text.lower()


def test_custom_prefix_and_health_remain_unchanged_with_postgresql(
    postgresql_url: URL,
    clean_postgresql: None,
) -> None:
    prefix = "/custom/v1"
    with TestClient(
        create_app(postgresql_settings(postgresql_url, api_v1_prefix=prefix))
    ) as client:
        product_id = create_product(client, prefix=prefix)

        assert client.get(f"{prefix}/products/{product_id}").status_code == 200
        assert client.get("/api/v1/products").status_code == 404
        assert client.get("/health").json() == {
            "status": "ok",
            "service": "opsmind-postgresql-test",
            "environment": "test",
        }


def test_memory_applications_remain_isolated() -> None:
    settings = Settings(environment=Environment.TEST)
    with (
        TestClient(create_app(settings)) as first_client,
        TestClient(create_app(settings)) as second_client,
    ):
        product_id = create_product(first_client)
        seed_operational_flow(first_client, product_id)
        created = create_workflow_review(first_client, product_id)
        recommendation_id = str(created["recommendation_id"])

        assert first_client.get(f"/api/v1/products/{product_id}").status_code == 200
        assert (
            get_workflow_review(
                first_client,
                recommendation_id,
            )
            == created
        )

        assert second_client.get(f"/api/v1/products/{product_id}").status_code == 404
        assert (
            second_client.get(
                f"/api/v1/reorder-recommendations/{recommendation_id}"
            ).status_code
            == 404
        )
        assert (
            second_client.get(
                f"/api/v1/reorder-recommendations/{recommendation_id}/audit-events"
            ).status_code
            == 404
        )
