"""Tests for the read-only baseline-demand forecast HTTP contract."""

from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from opsmind.core.config import Environment, Settings
from opsmind.repositories.memory import InMemoryProductInventoryRepository
from tests.security import authenticated_test_client, create_authenticated_test_app

MISSING_PRODUCT_ID = "00000000-0000-0000-0000-000000000099"


def make_settings(api_v1_prefix: str = "/api/v1") -> Settings:
    """Return deterministic forecast API settings."""
    return Settings(
        application_name="OpsMind Forecast Test",
        service_name="opsmind-forecast-test-api",
        environment=Environment.TEST,
        debug=False,
        api_v1_prefix=api_v1_prefix,
    )


def make_client(api_v1_prefix: str = "/api/v1") -> TestClient:
    """Create one isolated test application."""
    return authenticated_test_client(
        create_authenticated_test_app(make_settings(api_v1_prefix))
    )


def create_product(
    client: TestClient,
    sku: str = "SENSOR-001",
    api_v1_prefix: str = "/api/v1",
) -> str:
    """Create a product and return its UUID string."""
    response = client.post(
        f"{api_v1_prefix}/products",
        json={
            "sku": sku,
            "name": f"Product {sku}",
            "unit_of_measure": "each",
            "lead_time_days": 7,
        },
    )
    assert response.status_code == 201
    return cast(str, response.json()["id"])


def add_demand(
    client: TestClient,
    product_id: str,
    *items: tuple[str, int],
    api_v1_prefix: str = "/api/v1",
) -> list[dict[str, object]]:
    """Store one demand batch and return its response."""
    response = client.post(
        f"{api_v1_prefix}/products/{product_id}/demand",
        json={
            "observations": [
                {"demand_date": demand_date, "quantity": quantity}
                for demand_date, quantity in items
            ]
        },
    )
    assert response.status_code == 201
    return cast(list[dict[str, object]], response.json())


def test_default_forecast_uses_latest_date_and_all_available_history() -> None:
    client = make_client()
    product_id = create_product(client)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 12),
        ("2026-07-02", 18),
        ("2026-07-03", 9),
        ("2026-07-04", 0),
        ("2026-07-10", 21),
    )

    response = client.get(f"/api/v1/products/{product_id}/forecast")

    assert response.status_code == 200
    assert response.json() == {
        "product_id": product_id,
        "method": "simple_mean",
        "as_of_date": "2026-07-10",
        "lookback_observations_requested": 7,
        "observations_used": 5,
        "training_start_date": "2026-07-01",
        "training_end_date": "2026-07-10",
        "average_daily_demand": 12.0,
        "horizon_days": 7,
        "forecast_quantity": 84.0,
    }


def test_explicit_cutoff_prevents_future_leakage_and_uses_requested_window() -> None:
    client = make_client()
    product_id = create_product(client)
    add_demand(
        client,
        product_id,
        ("2026-07-10", 21),
        ("2026-07-03", 9),
        ("2026-07-01", 12),
        ("2026-07-04", 0),
        ("2026-07-02", 18),
    )

    response = client.get(
        f"/api/v1/products/{product_id}/forecast"
        "?lookback_observations=4&horizon_days=7&as_of_date=2026-07-04"
    )

    assert response.status_code == 200
    assert response.json() == {
        "product_id": product_id,
        "method": "simple_mean",
        "as_of_date": "2026-07-04",
        "lookback_observations_requested": 4,
        "observations_used": 4,
        "training_start_date": "2026-07-01",
        "training_end_date": "2026-07-04",
        "average_daily_demand": 9.75,
        "horizon_days": 7,
        "forecast_quantity": 68.25,
    }


def test_recent_observation_lookback_counts_records_not_calendar_days() -> None:
    client = make_client()
    product_id = create_product(client)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 500),
        ("2026-07-02", 18),
        ("2026-07-10", 9),
    )

    response = client.get(
        f"/api/v1/products/{product_id}/forecast?lookback_observations=2&horizon_days=2"
    )

    assert response.status_code == 200
    assert response.json()["training_start_date"] == "2026-07-02"
    assert response.json()["training_end_date"] == "2026-07-10"
    assert response.json()["observations_used"] == 2
    assert response.json()["average_daily_demand"] == 13.5
    assert response.json()["forecast_quantity"] == 27.0


def test_fewer_observations_than_requested_and_one_observation_are_supported() -> None:
    client = make_client()
    product_id = create_product(client)
    add_demand(client, product_id, ("2026-07-10", 21))

    response = client.get(
        f"/api/v1/products/{product_id}/forecast"
        "?lookback_observations=365&horizon_days=3"
    )

    assert response.status_code == 200
    assert response.json()["lookback_observations_requested"] == 365
    assert response.json()["observations_used"] == 1
    assert response.json()["average_daily_demand"] == 21.0
    assert response.json()["forecast_quantity"] == 63.0


def test_recorded_zeroes_are_included_and_all_zero_history_stays_zero() -> None:
    client = make_client()
    product_id = create_product(client)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 0),
        ("2026-07-10", 0),
    )

    response = client.get(f"/api/v1/products/{product_id}/forecast")

    assert response.status_code == 200
    assert response.json()["observations_used"] == 2
    assert response.json()["average_daily_demand"] == 0.0
    assert response.json()["forecast_quantity"] == 0.0


def test_fractional_outputs_are_json_numbers_and_round_deterministically() -> None:
    client = make_client()
    product_id = create_product(client)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 1),
        ("2026-07-02", 0),
        ("2026-07-03", 0),
    )

    first = client.get(f"/api/v1/products/{product_id}/forecast?horizon_days=3")
    second = client.get(f"/api/v1/products/{product_id}/forecast?horizon_days=3")

    assert first.status_code == 200
    assert first.json() == second.json()
    assert first.json()["average_daily_demand"] == 0.33
    assert first.json()["forecast_quantity"] == 1.0
    assert isinstance(first.json()["average_daily_demand"], float)
    assert isinstance(first.json()["forecast_quantity"], float)


def test_exact_cutoff_observation_is_included() -> None:
    client = make_client()
    product_id = create_product(client)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 12),
        ("2026-07-02", 18),
    )

    response = client.get(
        f"/api/v1/products/{product_id}/forecast?as_of_date=2026-07-01"
    )

    assert response.status_code == 200
    assert response.json()["observations_used"] == 1
    assert response.json()["training_end_date"] == "2026-07-01"


def test_missing_product_returns_existing_safe_404_contract() -> None:
    response = make_client().get(f"/api/v1/products/{MISSING_PRODUCT_ID}/forecast")

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Product '{MISSING_PRODUCT_ID}' was not found."
    }


def test_existing_product_without_history_returns_safe_422_detail() -> None:
    client = make_client()
    product_id = create_product(client)

    response = client.get(f"/api/v1/products/{product_id}/forecast")

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "At least one demand observation is required to calculate a forecast "
            f"for product '{product_id}'."
        )
    }


def test_cutoff_before_all_history_returns_safe_422_detail() -> None:
    client = make_client()
    product_id = create_product(client)
    add_demand(client, product_id, ("2026-07-02", 18))

    response = client.get(
        f"/api/v1/products/{product_id}/forecast?as_of_date=2026-07-01"
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            f"No demand observations are available for product '{product_id}' "
            "on or before '2026-07-01'."
        )
    }


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/products/not-a-uuid/forecast",
        f"/api/v1/products/{MISSING_PRODUCT_ID}/forecast?as_of_date=not-a-date",
        f"/api/v1/products/{MISSING_PRODUCT_ID}/forecast?lookback_observations=0",
        f"/api/v1/products/{MISSING_PRODUCT_ID}/forecast?lookback_observations=-1",
        f"/api/v1/products/{MISSING_PRODUCT_ID}/forecast?lookback_observations=366",
        f"/api/v1/products/{MISSING_PRODUCT_ID}/forecast?horizon_days=0",
        f"/api/v1/products/{MISSING_PRODUCT_ID}/forecast?horizon_days=-1",
        f"/api/v1/products/{MISSING_PRODUCT_ID}/forecast?horizon_days=366",
    ],
)
def test_invalid_path_and_query_values_return_422(path: str) -> None:
    assert make_client().get(path).status_code == 422


def test_forecast_is_read_only_and_existing_routes_remain_exact() -> None:
    client = make_client()
    product_id = create_product(client)
    demand_before = add_demand(
        client,
        product_id,
        ("2026-07-01", 12),
        ("2026-07-03", 9),
    )
    inventory_before = client.put(
        f"/api/v1/products/{product_id}/inventory",
        json={"on_hand_quantity": 20, "allocated_quantity": 30},
    ).json()
    product_before = client.get(f"/api/v1/products/{product_id}").json()

    forecast_response = client.get(f"/api/v1/products/{product_id}/forecast")

    assert forecast_response.status_code == 200
    assert client.get(f"/api/v1/products/{product_id}").json() == product_before
    assert client.get(f"/api/v1/products/{product_id}/inventory").json() == (
        inventory_before
    )
    assert client.get(f"/api/v1/products/{product_id}/demand").json() == demand_before
    assert inventory_before["available_quantity"] == -10
    assert client.get("/health").json() == {
        "status": "ok",
        "service": "opsmind-forecast-test-api",
        "environment": "test",
    }


def test_custom_api_prefix_applies_without_version_root_or_health_change() -> None:
    client = make_client("/supply/v2")
    product_id = create_product(client, api_v1_prefix="/supply/v2")
    add_demand(
        client,
        product_id,
        ("2026-07-01", 12),
        api_v1_prefix="/supply/v2",
    )

    assert client.get(f"/supply/v2/products/{product_id}/forecast").status_code == 200
    assert client.get(f"/api/v1/products/{product_id}/forecast").status_code == 404
    assert client.get("/supply/v2").status_code == 404
    assert client.get("/health").status_code == 200


def test_separate_applications_do_not_share_forecast_inputs() -> None:
    first_client = make_client()
    second_client = make_client()
    first_id = create_product(first_client)
    second_id = create_product(second_client)
    add_demand(first_client, first_id, ("2026-07-01", 12))

    assert first_client.get(f"/api/v1/products/{first_id}/forecast").status_code == 200
    assert (
        second_client.get(f"/api/v1/products/{second_id}/forecast").status_code == 422
    )


def test_all_business_routes_use_the_injected_repository() -> None:
    repository = InMemoryProductInventoryRepository()
    client = authenticated_test_client(
        create_authenticated_test_app(
            make_settings(),
            product_inventory_repository=repository,
        )
    )
    product_id = create_product(client)
    add_demand(client, product_id, ("2026-07-01", 12))
    before = repository.list_demand_observations(UUID(product_id))

    response = client.get(f"/api/v1/products/{product_id}/forecast")

    assert response.status_code == 200
    assert response.json()["average_daily_demand"] == 12.0
    assert repository.get_product(UUID(product_id)).sku == "SENSOR-001"
    assert repository.list_demand_observations(UUID(product_id)) == before


def test_openapi_documents_forecast_contract_and_parameter_constraints() -> None:
    schema = make_client().get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/products/{product_id}/forecast"]["get"]
    parameters = {item["name"]: item["schema"] for item in operation["parameters"]}

    assert set(operation["responses"]) >= {"200", "404", "422"}
    assert parameters["lookback_observations"] == {
        "type": "integer",
        "maximum": 365,
        "minimum": 1,
        "description": "Number of recent eligible demand observations to use.",
        "default": 7,
        "title": "Lookback Observations",
    }
    assert parameters["horizon_days"] == {
        "type": "integer",
        "maximum": 365,
        "minimum": 1,
        "description": "Number of future days covered by the forecast.",
        "default": 7,
        "title": "Horizon Days",
    }
    assert "as_of_date" in parameters
    response_schema = schema["components"]["schemas"]["ForecastResponse"]
    properties = response_schema["properties"]
    for field in (
        "as_of_date",
        "training_start_date",
        "training_end_date",
    ):
        assert properties[field]["type"] == "string"
        assert properties[field]["format"] == "date"
    assert properties["average_daily_demand"]["type"] == "number"
    assert properties["forecast_quantity"]["type"] == "number"
    method_schema = schema["components"]["schemas"]["ForecastMethod"]
    assert method_schema["enum"] == ["simple_mean"]
