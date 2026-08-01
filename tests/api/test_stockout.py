"""Tests for the read-only deterministic stockout-exposure HTTP contract."""

from datetime import date, timedelta
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from opsmind.application import create_app
from opsmind.core.config import Environment, Settings
from opsmind.repositories.memory import InMemoryProductInventoryRepository

MISSING_PRODUCT_ID = "00000000-0000-0000-0000-000000000099"


def make_settings(api_v1_prefix: str = "/api/v1") -> Settings:
    """Return deterministic stockout API settings."""
    return Settings(
        application_name="OpsMind Stockout Test",
        service_name="opsmind-stockout-test-api",
        environment=Environment.TEST,
        debug=False,
        api_v1_prefix=api_v1_prefix,
    )


def make_client(api_v1_prefix: str = "/api/v1") -> TestClient:
    """Create one isolated test application."""
    return TestClient(create_app(make_settings(api_v1_prefix)))


def create_product(
    client: TestClient,
    sku: str = "SENSOR-001",
    lead_time_days: int = 5,
    api_v1_prefix: str = "/api/v1",
) -> str:
    """Create a product and return its UUID string."""
    response = client.post(
        f"{api_v1_prefix}/products",
        json={
            "sku": sku,
            "name": f"Product {sku}",
            "unit_of_measure": "each",
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
    api_v1_prefix: str = "/api/v1",
) -> dict[str, object]:
    """Set inventory and return the response body."""
    response = client.put(
        f"{api_v1_prefix}/products/{product_id}/inventory",
        json={
            "on_hand_quantity": on_hand_quantity,
            "allocated_quantity": allocated_quantity,
        },
    )
    assert response.status_code == 200
    return cast(dict[str, object], response.json())


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


def add_standard_demand(client: TestClient, product_id: str) -> None:
    """Store the issue's five-observation demand history."""
    add_demand(
        client,
        product_id,
        ("2026-07-01", 12),
        ("2026-07-02", 18),
        ("2026-07-03", 9),
        ("2026-07-04", 0),
        ("2026-07-10", 21),
    )


def exposure_path(product_id: str) -> str:
    """Return the default stockout-exposure path."""
    return f"/api/v1/products/{product_id}/stockout-exposure"


def test_explicit_cutoff_returns_complete_positive_exposure() -> None:
    client = make_client()
    product_id = create_product(client)
    set_inventory(client, product_id, 60, 10)
    add_standard_demand(client, product_id)

    response = client.get(
        exposure_path(product_id) + "?lookback_observations=4&as_of_date=2026-07-04"
    )

    assert response.status_code == 200
    assert response.json() == {
        "product_id": product_id,
        "forecast_method": "simple_mean",
        "as_of_date": "2026-07-04",
        "lookback_observations_requested": 4,
        "observations_used": 4,
        "training_start_date": "2026-07-01",
        "training_end_date": "2026-07-04",
        "average_daily_demand": 9.75,
        "lead_time_days": 5,
        "on_hand_quantity": 60,
        "allocated_quantity": 10,
        "available_inventory": 50,
        "forecasted_lead_time_demand": 48.75,
        "projected_inventory_balance": 1.25,
        "projected_shortage_quantity": 0.0,
        "status": "sufficient",
    }


def test_default_lookback_and_latest_date_cutoff_are_used() -> None:
    client = make_client()
    product_id = create_product(client, lead_time_days=1)
    set_inventory(client, product_id, 100, 0)
    add_standard_demand(client, product_id)

    response = client.get(exposure_path(product_id))

    assert response.status_code == 200
    body = response.json()
    assert body["as_of_date"] == "2026-07-10"
    assert body["lookback_observations_requested"] == 7
    assert body["observations_used"] == 5
    assert body["training_start_date"] == "2026-07-01"
    assert body["training_end_date"] == "2026-07-10"
    assert body["average_daily_demand"] == 12.0
    assert body["forecasted_lead_time_demand"] == 12.0


def test_recent_record_selection_excludes_future_and_does_not_impute_dates() -> None:
    client = make_client()
    product_id = create_product(client, lead_time_days=2)
    set_inventory(client, product_id, 100, 0)
    add_demand(
        client,
        product_id,
        ("2026-07-10", 100),
        ("2026-07-03", 9),
        ("2026-07-01", 12),
        ("2026-07-02", 18),
    )

    response = client.get(
        exposure_path(product_id) + "?lookback_observations=2&as_of_date=2026-07-03"
    )

    assert response.status_code == 200
    body = response.json()
    assert body["observations_used"] == 2
    assert body["training_start_date"] == "2026-07-02"
    assert body["training_end_date"] == "2026-07-03"
    assert body["average_daily_demand"] == 13.5
    assert body["forecasted_lead_time_demand"] == 27.0


def test_fewer_observations_than_requested_uses_all_records() -> None:
    client = make_client()
    product_id = create_product(client, lead_time_days=1)
    set_inventory(client, product_id, 100, 0)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 12),
        ("2026-07-10", 18),
    )

    response = client.get(exposure_path(product_id) + "?lookback_observations=365")

    assert response.status_code == 200
    assert response.json()["lookback_observations_requested"] == 365
    assert response.json()["observations_used"] == 2
    assert response.json()["average_daily_demand"] == 15.0


def test_exact_zero_balance_is_sufficient() -> None:
    client = make_client()
    product_id = create_product(client)
    set_inventory(client, product_id, 60, 10)
    add_demand(client, product_id, ("2026-07-01", 10))

    response = client.get(exposure_path(product_id))

    assert response.status_code == 200
    assert response.json()["projected_inventory_balance"] == 0.0
    assert response.json()["projected_shortage_quantity"] == 0.0
    assert response.json()["status"] == "sufficient"


def test_negative_balance_returns_positive_shortage() -> None:
    client = make_client()
    product_id = create_product(client)
    set_inventory(client, product_id, 40, 10)
    add_standard_demand(client, product_id)

    response = client.get(
        exposure_path(product_id) + "?lookback_observations=4&as_of_date=2026-07-04"
    )

    assert response.status_code == 200
    assert response.json()["available_inventory"] == 30
    assert response.json()["projected_inventory_balance"] == -18.75
    assert response.json()["projected_shortage_quantity"] == 18.75
    assert response.json()["status"] == "shortage_projected"


def test_negative_existing_availability_is_not_clamped() -> None:
    client = make_client()
    product_id = create_product(client)
    set_inventory(client, product_id, 20, 30)
    add_demand(client, product_id, ("2026-07-01", 2))

    response = client.get(exposure_path(product_id))

    assert response.status_code == 200
    assert response.json()["available_inventory"] == -10
    assert response.json()["projected_inventory_balance"] == -20.0
    assert response.json()["projected_shortage_quantity"] == 20.0
    assert response.json()["status"] == "shortage_projected"


@pytest.mark.parametrize(
    (
        "on_hand_quantity",
        "allocated_quantity",
        "expected_balance",
        "expected_shortage",
        "expected_status",
    ),
    [
        (20, 10, 10.0, 0.0, "sufficient"),
        (10, 10, 0.0, 0.0, "sufficient"),
        (10, 20, -10.0, 10.0, "shortage_projected"),
    ],
)
def test_zero_lead_time_uses_current_availability(
    on_hand_quantity: int,
    allocated_quantity: int,
    expected_balance: float,
    expected_shortage: float,
    expected_status: str,
) -> None:
    client = make_client()
    product_id = create_product(client, lead_time_days=0)
    set_inventory(client, product_id, on_hand_quantity, allocated_quantity)
    add_demand(client, product_id, ("2026-07-01", 99))

    response = client.get(exposure_path(product_id))

    assert response.status_code == 200
    assert response.json()["lead_time_days"] == 0
    assert response.json()["forecasted_lead_time_demand"] == 0.0
    assert response.json()["projected_inventory_balance"] == expected_balance
    assert response.json()["projected_shortage_quantity"] == expected_shortage
    assert response.json()["status"] == expected_status


def test_large_product_lead_time_above_365_is_supported() -> None:
    client = make_client()
    product_id = create_product(client, lead_time_days=500)
    set_inventory(client, product_id, 1200, 0)
    add_demand(client, product_id, ("2026-07-01", 2))

    response = client.get(exposure_path(product_id))

    assert response.status_code == 200
    assert response.json()["lead_time_days"] == 500
    assert response.json()["forecasted_lead_time_demand"] == 1000.0
    assert response.json()["projected_inventory_balance"] == 200.0


def test_recorded_zeroes_and_all_zero_history_remain_zero() -> None:
    client = make_client()
    product_id = create_product(client, lead_time_days=30)
    set_inventory(client, product_id, 0, 0)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 0),
        ("2026-07-10", 0),
    )

    response = client.get(exposure_path(product_id))

    assert response.status_code == 200
    assert response.json()["observations_used"] == 2
    assert response.json()["average_daily_demand"] == 0.0
    assert response.json()["forecasted_lead_time_demand"] == 0.0
    assert response.json()["projected_inventory_balance"] == 0.0


def test_exact_mean_prevents_premature_rounding() -> None:
    client = make_client()
    product_id = create_product(client, lead_time_days=3)
    set_inventory(client, product_id, 1, 0)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 1),
        ("2026-07-02", 0),
        ("2026-07-03", 0),
    )

    response = client.get(exposure_path(product_id))

    assert response.status_code == 200
    assert response.json()["average_daily_demand"] == 0.33
    assert response.json()["forecasted_lead_time_demand"] == 1.0
    assert response.json()["projected_inventory_balance"] == 0.0
    assert response.json()["status"] == "sufficient"
    assert isinstance(response.json()["average_daily_demand"], float)
    assert isinstance(response.json()["forecasted_lead_time_demand"], float)


def test_negative_zero_is_normalized_in_public_response() -> None:
    client = make_client()
    product_id = create_product(client, lead_time_days=1)
    set_inventory(client, product_id, 0, 0)
    first_date = date(2025, 1, 1)
    add_demand(
        client,
        product_id,
        *tuple(
            (
                (first_date + timedelta(days=index)).isoformat(),
                1 if index == 0 else 0,
            )
            for index in range(365)
        ),
    )

    response = client.get(exposure_path(product_id) + "?lookback_observations=365")

    assert response.status_code == 200
    assert response.json()["forecasted_lead_time_demand"] == 0.0
    assert response.json()["projected_inventory_balance"] == 0.0
    assert response.json()["projected_shortage_quantity"] == 0.0
    assert response.json()["status"] == "sufficient"


def test_missing_product_returns_existing_safe_404() -> None:
    response = make_client().get(exposure_path(MISSING_PRODUCT_ID))

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Product '{MISSING_PRODUCT_ID}' was not found."
    }


def test_missing_inventory_returns_distinct_safe_404() -> None:
    client = make_client()
    product_id = create_product(client)

    response = client.get(exposure_path(product_id))

    assert response.status_code == 404
    assert response.json() == {
        "detail": f"Inventory for product '{product_id}' was not found."
    }


def test_existing_product_without_demand_returns_safe_422() -> None:
    client = make_client()
    product_id = create_product(client)
    set_inventory(client, product_id, 10, 0)

    response = client.get(exposure_path(product_id))

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "At least one demand observation is required to calculate a forecast "
            f"for product '{product_id}'."
        )
    }


def test_cutoff_before_all_demand_returns_safe_422() -> None:
    client = make_client()
    product_id = create_product(client)
    set_inventory(client, product_id, 10, 0)
    add_demand(client, product_id, ("2026-07-02", 3))

    response = client.get(exposure_path(product_id) + "?as_of_date=2026-07-01")

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
        "/api/v1/products/not-a-uuid/stockout-exposure",
        f"{exposure_path(MISSING_PRODUCT_ID)}?as_of_date=not-a-date",
        f"{exposure_path(MISSING_PRODUCT_ID)}?lookback_observations=0",
        f"{exposure_path(MISSING_PRODUCT_ID)}?lookback_observations=-1",
        f"{exposure_path(MISSING_PRODUCT_ID)}?lookback_observations=366",
    ],
)
def test_invalid_path_and_query_values_return_422(path: str) -> None:
    assert make_client().get(path).status_code == 422


def test_exposure_is_read_only_and_existing_routes_remain_exact() -> None:
    client = make_client()
    product_id = create_product(client)
    inventory_before = set_inventory(client, product_id, 60, 10)
    demand_before = add_demand(
        client,
        product_id,
        ("2026-07-01", 12),
        ("2026-07-02", 18),
        ("2026-07-03", 9),
        ("2026-07-04", 0),
    )
    product_before = client.get(f"/api/v1/products/{product_id}").json()
    forecast_before = client.get(
        f"/api/v1/products/{product_id}/forecast"
        "?lookback_observations=4&horizon_days=7&as_of_date=2026-07-04"
    ).json()

    first = client.get(
        exposure_path(product_id) + "?lookback_observations=4&as_of_date=2026-07-04"
    )
    second = client.get(
        exposure_path(product_id) + "?lookback_observations=4&as_of_date=2026-07-04"
    )

    assert first.status_code == 200
    assert first.json() == second.json()
    assert client.get(f"/api/v1/products/{product_id}").json() == product_before
    assert client.get(f"/api/v1/products/{product_id}/inventory").json() == (
        inventory_before
    )
    assert client.get(f"/api/v1/products/{product_id}/demand").json() == demand_before
    assert (
        client.get(
            f"/api/v1/products/{product_id}/forecast"
            "?lookback_observations=4&horizon_days=7&as_of_date=2026-07-04"
        ).json()
        == forecast_before
    )
    assert forecast_before["average_daily_demand"] == 9.75
    assert forecast_before["forecast_quantity"] == 68.25
    assert client.get("/health").json() == {
        "status": "ok",
        "service": "opsmind-stockout-test-api",
        "environment": "test",
    }


def test_custom_api_prefix_applies_without_health_or_version_root_change() -> None:
    prefix = "/supply/v2"
    client = make_client(prefix)
    product_id = create_product(client, api_v1_prefix=prefix)
    set_inventory(client, product_id, 10, 0, api_v1_prefix=prefix)
    add_demand(
        client,
        product_id,
        ("2026-07-01", 1),
        api_v1_prefix=prefix,
    )

    assert (
        client.get(f"{prefix}/products/{product_id}/stockout-exposure").status_code
        == 200
    )
    assert client.get(exposure_path(product_id)).status_code == 404
    assert client.get(prefix).status_code == 404
    assert client.get("/health").status_code == 200


def test_separate_applications_do_not_share_exposure_inputs() -> None:
    first_client = make_client()
    second_client = make_client()
    first_id = create_product(first_client)
    second_id = create_product(second_client)
    set_inventory(first_client, first_id, 10, 0)
    set_inventory(second_client, second_id, 10, 0)
    add_demand(first_client, first_id, ("2026-07-01", 1))

    assert first_client.get(exposure_path(first_id)).status_code == 200
    assert second_client.get(exposure_path(second_id)).status_code == 422


def test_all_business_routes_use_the_injected_repository() -> None:
    repository = InMemoryProductInventoryRepository()
    client = TestClient(create_app(make_settings(), repository))
    product_id = create_product(client)
    set_inventory(client, product_id, 10, 0)
    add_demand(client, product_id, ("2026-07-01", 1))
    product_before = repository.get_product(UUID(product_id))
    inventory_before = repository.get_inventory(UUID(product_id))
    demand_before = repository.list_demand_observations(UUID(product_id))

    response = client.get(exposure_path(product_id))

    assert response.status_code == 200
    assert response.json()["available_inventory"] == 10
    assert repository.get_product(UUID(product_id)) == product_before
    assert repository.get_inventory(UUID(product_id)) == inventory_before
    assert repository.list_demand_observations(UUID(product_id)) == demand_before


def test_openapi_documents_stockout_contract_without_probability_or_reorder() -> None:
    schema = make_client().get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/products/{product_id}/stockout-exposure"][
        "get"
    ]
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
    assert "as_of_date" in parameters
    response_schema = schema["components"]["schemas"]["StockoutExposureResponse"]
    properties = response_schema["properties"]
    for field in ("as_of_date", "training_start_date", "training_end_date"):
        assert properties[field]["type"] == "string"
        assert properties[field]["format"] == "date"
    for field in (
        "average_daily_demand",
        "forecasted_lead_time_demand",
        "projected_inventory_balance",
        "projected_shortage_quantity",
    ):
        assert properties[field]["type"] == "number"
    assert "probability" not in properties
    assert "reorder_quantity" not in properties
    assert schema["components"]["schemas"]["ForecastMethod"]["enum"] == ["simple_mean"]
    assert schema["components"]["schemas"]["StockoutExposureStatus"]["enum"] == [
        "sufficient",
        "shortage_projected",
    ]
