"""PostgreSQL-backed application sharing, durability, and analytical tests."""

from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.engine import URL

from opsmind.application import create_app
from opsmind.core.config import Environment, PersistenceBackend, Settings


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


def test_shared_operational_state_restart_durability_and_workflow_isolation(
    postgresql_url: URL,
    clean_postgresql: None,
) -> None:
    settings = postgresql_settings(postgresql_url)
    recommendation_id: str

    with TestClient(create_app(settings)) as first_client:
        product_id = create_product(first_client)
        seed_operational_flow(first_client, product_id)
        assert_analytical_flow(first_client, product_id)
        review = first_client.post(
            f"/api/v1/products/{product_id}/reorder-recommendations",
            params={
                "lookback_observations": 4,
                "as_of_date": "2026-07-04",
            },
        )
        assert review.status_code == 201
        recommendation_id = str(review.json()["recommendation_id"])
        assert (
            first_client.get(
                f"/api/v1/reorder-recommendations/{recommendation_id}/audit-events"
            ).status_code
            == 200
        )

        with TestClient(create_app(settings)) as second_client:
            assert (
                second_client.get(f"/api/v1/products/{product_id}").status_code == 200
            )
            assert_analytical_flow(second_client, product_id)
            assert (
                second_client.get(
                    f"/api/v1/reorder-recommendations/{recommendation_id}"
                ).status_code
                == 404
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

    with TestClient(create_app(settings)) as restarted_client:
        assert restarted_client.get(f"/api/v1/products/{product_id}").status_code == 200
        assert (
            len(restarted_client.get(f"/api/v1/products/{product_id}/demand").json())
            == 5
        )
        assert (
            restarted_client.get(
                f"/api/v1/reorder-recommendations/{recommendation_id}"
            ).status_code
            == 404
        )
        assert_analytical_flow(restarted_client, product_id)


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
        assert first_client.get(f"/api/v1/products/{product_id}").status_code == 200
        assert second_client.get(f"/api/v1/products/{product_id}").status_code == 404
