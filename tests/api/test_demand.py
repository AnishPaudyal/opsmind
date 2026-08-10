"""Tests for demand-history ingestion and retrieval HTTP contracts."""

from datetime import date
from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from opsmind.core.config import Environment, Settings
from opsmind.repositories.memory import InMemoryProductInventoryRepository
from tests.security import authenticated_test_client, create_authenticated_test_app

MISSING_PRODUCT_ID = "00000000-0000-0000-0000-000000000099"


def make_settings(api_v1_prefix: str = "/api/v1") -> Settings:
    """Return deterministic settings for demand API tests."""
    return Settings(
        application_name="OpsMind Test",
        service_name="opsmind-test-api",
        environment=Environment.TEST,
        debug=False,
        api_v1_prefix=api_v1_prefix,
    )


def make_client(api_v1_prefix: str = "/api/v1") -> TestClient:
    """Create an isolated test application."""
    return authenticated_test_client(
        create_authenticated_test_app(make_settings(api_v1_prefix))
    )


def create_product(
    client: TestClient,
    sku: str = "SENSOR-001",
    api_v1_prefix: str = "/api/v1",
) -> str:
    """Create a product and return its server-generated UUID."""
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


def demand_payload(*items: tuple[str, int]) -> dict[str, object]:
    """Create an API demand-batch payload."""
    return {
        "observations": [
            {"demand_date": demand_date, "quantity": quantity}
            for demand_date, quantity in items
        ]
    }


def test_ingest_one_observation_returns_explicit_201_response() -> None:
    client = make_client()
    product_id = create_product(client)

    response = client.post(
        f"/api/v1/products/{product_id}/demand",
        json=demand_payload(("2026-07-01", 12)),
    )

    assert response.status_code == 201
    assert response.json() == [
        {
            "product_id": product_id,
            "demand_date": "2026-07-01",
            "quantity": 12,
        }
    ]


def test_unsorted_batch_is_returned_chronologically_and_zero_is_valid() -> None:
    client = make_client()
    product_id = create_product(client)

    response = client.post(
        f"/api/v1/products/{product_id}/demand",
        json=demand_payload(
            ("2026-07-03", 9),
            ("2026-07-01", 12),
            ("2026-07-02", 0),
        ),
    )

    assert response.status_code == 201
    assert [item["demand_date"] for item in response.json()] == [
        "2026-07-01",
        "2026-07-02",
        "2026-07-03",
    ]
    assert response.json()[1]["quantity"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"observations": []},
        {},
        demand_payload(("2026-07-01", -1)),
        demand_payload(("not-a-date", 1)),
        {
            "observations": [
                {"demand_date": "2026-07-01", "quantity": 1.5},
            ]
        },
    ],
)
def test_invalid_ingestion_payloads_return_422(payload: dict[str, object]) -> None:
    client = make_client()
    product_id = create_product(client)

    response = client.post(
        f"/api/v1/products/{product_id}/demand",
        json=payload,
    )

    assert response.status_code == 422


def test_invalid_uuid_and_missing_product_are_distinct() -> None:
    client = make_client()
    payload = demand_payload(("2026-07-01", 12))

    invalid_response = client.post("/api/v1/products/not-a-uuid/demand", json=payload)
    missing_response = client.post(
        f"/api/v1/products/{MISSING_PRODUCT_ID}/demand",
        json=payload,
    )

    assert invalid_response.status_code == 422
    assert missing_response.status_code == 404
    assert missing_response.json() == {
        "detail": f"Product '{MISSING_PRODUCT_ID}' was not found."
    }


def test_duplicate_date_inside_request_returns_safe_409_without_storage() -> None:
    client = make_client()
    product_id = create_product(client)

    response = client.post(
        f"/api/v1/products/{product_id}/demand",
        json=demand_payload(("2026-07-01", 12), ("2026-07-01", 18)),
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": (f"Demand for product '{product_id}' on '2026-07-01' already exists.")
    }
    assert client.get(f"/api/v1/products/{product_id}/demand").json() == []


def test_existing_date_conflict_is_atomic() -> None:
    client = make_client()
    product_id = create_product(client)
    path = f"/api/v1/products/{product_id}/demand"
    first_response = client.post(path, json=demand_payload(("2026-07-01", 12)))
    assert first_response.status_code == 201

    conflict_response = client.post(
        path,
        json=demand_payload(("2026-07-02", 18), ("2026-07-01", 99)),
    )

    assert conflict_response.status_code == 409
    assert client.get(path).json() == first_response.json()


def test_same_date_can_be_stored_for_different_products() -> None:
    client = make_client()
    first_id = create_product(client, "SENSOR-001")
    second_id = create_product(client, "ACTUATOR-001")
    payload = demand_payload(("2026-07-01", 12))

    first_response = client.post(
        f"/api/v1/products/{first_id}/demand",
        json=payload,
    )
    second_response = client.post(
        f"/api/v1/products/{second_id}/demand",
        json=payload,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201


def test_existing_product_without_demand_returns_empty_list() -> None:
    client = make_client()
    product_id = create_product(client)

    response = client.get(f"/api/v1/products/{product_id}/demand")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.parametrize(
    ("query", "expected_dates"),
    [
        ("", ["2026-07-01", "2026-07-02", "2026-07-03"]),
        ("?start_date=2026-07-02", ["2026-07-02", "2026-07-03"]),
        ("?end_date=2026-07-02", ["2026-07-01", "2026-07-02"]),
        (
            "?start_date=2026-07-02&end_date=2026-07-03",
            ["2026-07-02", "2026-07-03"],
        ),
        ("?start_date=2026-07-02&end_date=2026-07-02", ["2026-07-02"]),
        ("?start_date=2026-08-01&end_date=2026-08-31", []),
    ],
)
def test_chronological_retrieval_and_inclusive_filters(
    query: str,
    expected_dates: list[str],
) -> None:
    client = make_client()
    product_id = create_product(client)
    path = f"/api/v1/products/{product_id}/demand"
    client.post(
        path,
        json=demand_payload(
            ("2026-07-03", 9),
            ("2026-07-01", 12),
            ("2026-07-02", 18),
        ),
    )

    response = client.get(f"{path}{query}")

    assert response.status_code == 200
    assert [item["demand_date"] for item in response.json()] == expected_dates


def test_retrieval_validation_and_missing_product_errors() -> None:
    client = make_client()
    product_id = create_product(client)

    reversed_response = client.get(
        f"/api/v1/products/{product_id}/demand"
        "?start_date=2026-07-02&end_date=2026-07-01"
    )
    invalid_date_response = client.get(
        f"/api/v1/products/{product_id}/demand?start_date=not-a-date"
    )
    missing_response = client.get(f"/api/v1/products/{MISSING_PRODUCT_ID}/demand")
    invalid_uuid_response = client.get("/api/v1/products/not-a-uuid/demand")

    assert reversed_response.status_code == 422
    assert reversed_response.json() == {
        "detail": "start_date must be on or before end_date"
    }
    assert invalid_date_response.status_code == 422
    assert missing_response.status_code == 404
    assert invalid_uuid_response.status_code == 422


def test_product_inventory_and_health_regressions() -> None:
    client = make_client()
    product_id = create_product(client)

    product_response = client.get(f"/api/v1/products/{product_id}")
    inventory_response = client.put(
        f"/api/v1/products/{product_id}/inventory",
        json={"on_hand_quantity": 20, "allocated_quantity": 30},
    )
    health_response = client.get("/health")

    assert product_response.status_code == 200
    assert inventory_response.status_code == 200
    assert inventory_response.json()["available_quantity"] == -10
    assert health_response.json() == {
        "status": "ok",
        "service": "opsmind-test-api",
        "environment": "test",
    }


def test_custom_api_prefix_applies_to_demand_without_version_root() -> None:
    client = make_client("/supply/v2")
    product_id = create_product(client, api_v1_prefix="/supply/v2")

    assert client.get(f"/supply/v2/products/{product_id}/demand").status_code == 200
    assert client.get(f"/api/v1/products/{product_id}/demand").status_code == 404
    assert client.get("/supply/v2").status_code == 404
    assert client.get("/health").status_code == 200


def test_openapi_documents_both_demand_operations_and_schemas() -> None:
    schema = make_client().get("/openapi.json").json()
    demand_path = schema["paths"]["/api/v1/products/{product_id}/demand"]

    assert set(demand_path) == {"get", "post"}
    assert set(demand_path["post"]["responses"]) >= {"201", "404", "409", "422"}
    assert set(demand_path["get"]["responses"]) >= {"200", "404", "422"}
    assert {
        "DemandObservationCreate",
        "DemandBatchCreate",
        "DemandObservationResponse",
    } <= set(schema["components"]["schemas"])
    quantity_schema = schema["components"]["schemas"]["DemandObservationCreate"][
        "properties"
    ]["quantity"]
    date_schema = schema["components"]["schemas"]["DemandObservationCreate"][
        "properties"
    ]["demand_date"]
    assert quantity_schema["minimum"] == 0
    assert quantity_schema["type"] == "integer"
    assert date_schema["type"] == "string"
    assert date_schema["format"] == "date"


def test_separate_applications_do_not_share_demand() -> None:
    first_client = make_client()
    second_client = make_client()
    first_id = create_product(first_client)
    second_id = create_product(second_client)
    first_client.post(
        f"/api/v1/products/{first_id}/demand",
        json=demand_payload(("2026-07-01", 12)),
    )

    assert len(first_client.get(f"/api/v1/products/{first_id}/demand").json()) == 1
    assert second_client.get(f"/api/v1/products/{second_id}/demand").json() == []


def test_product_inventory_and_demand_share_injected_repository() -> None:
    repository = InMemoryProductInventoryRepository()
    client = authenticated_test_client(
        create_authenticated_test_app(
            make_settings(),
            product_inventory_repository=repository,
        )
    )
    product_id = create_product(client)
    response = client.post(
        f"/api/v1/products/{product_id}/demand",
        json=demand_payload(("2026-07-01", 12)),
    )

    assert response.status_code == 201
    stored = repository.list_demand_observations(
        UUID(product_id),
    )
    assert stored[0].demand_date == date(2026, 7, 1)
