"""Tests for product and inventory HTTP contracts."""

from typing import cast
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from opsmind.application import create_app
from opsmind.core.config import Environment, Settings

MISSING_PRODUCT_ID = "00000000-0000-0000-0000-000000000099"


def make_test_settings(api_v1_prefix: str = "/api/v1") -> Settings:
    """Return deterministic settings for API tests."""
    return Settings(
        application_name="OpsMind Test",
        service_name="opsmind-test-api",
        environment=Environment.TEST,
        debug=False,
        api_v1_prefix=api_v1_prefix,
    )


def create_test_client(api_v1_prefix: str = "/api/v1") -> TestClient:
    """Create an isolated application client."""
    return TestClient(create_app(make_test_settings(api_v1_prefix)))


def product_payload(sku: str = "SENSOR-001") -> dict[str, object]:
    """Return a valid product request payload."""
    return {
        "sku": sku,
        "name": " Temperature Sensor ",
        "unit_of_measure": " each ",
        "lead_time_days": 14,
    }


def create_product(client: TestClient, sku: str = "SENSOR-001") -> dict[str, object]:
    """Create and return a product after asserting successful creation."""
    response = client.post("/api/v1/products", json=product_payload(sku))
    assert response.status_code == 201
    return cast(dict[str, object], response.json())


def test_create_product_returns_normalized_explicit_response() -> None:
    client = create_test_client()

    response = client.post("/api/v1/products", json=product_payload(" sensor-001 "))

    assert response.status_code == 201
    body = response.json()
    UUID(body["id"])
    assert body == {
        "id": body["id"],
        "sku": "SENSOR-001",
        "name": "Temperature Sensor",
        "unit_of_measure": "each",
        "lead_time_days": 14,
        "is_active": True,
    }


def test_duplicate_normalized_sku_returns_conflict() -> None:
    client = create_test_client()
    create_product(client, "SENSOR-001")

    response = client.post("/api/v1/products", json=product_payload(" sensor-001 "))

    assert response.status_code == 409
    assert response.json() == {
        "detail": "A product with SKU 'SENSOR-001' already exists."
    }


@pytest.mark.parametrize(
    "payload",
    [
        {**product_payload(), "sku": ""},
        {**product_payload(), "sku": "   "},
        {**product_payload(), "name": ""},
        {**product_payload(), "name": "   "},
        {**product_payload(), "unit_of_measure": ""},
        {**product_payload(), "unit_of_measure": "   "},
        {**product_payload(), "lead_time_days": -1},
    ],
)
def test_invalid_product_fields_return_unprocessable_content(
    payload: dict[str, object],
) -> None:
    response = create_test_client().post("/api/v1/products", json=payload)

    assert response.status_code == 422


def test_product_list_is_empty_then_deterministic() -> None:
    client = create_test_client()
    assert client.get("/api/v1/products").json() == []
    create_product(client, "ZZZ-001")
    create_product(client, "AAA-001")

    response = client.get("/api/v1/products")

    assert response.status_code == 200
    assert [item["sku"] for item in response.json()] == ["AAA-001", "ZZZ-001"]


def test_product_retrieval_and_path_errors() -> None:
    client = create_test_client()
    created = create_product(client)

    response = client.get(f"/api/v1/products/{created['id']}")
    missing_response = client.get(f"/api/v1/products/{MISSING_PRODUCT_ID}")
    invalid_response = client.get("/api/v1/products/not-a-uuid")

    assert response.status_code == 200
    assert response.json() == created
    assert missing_response.status_code == 404
    assert missing_response.json() == {
        "detail": f"Product '{MISSING_PRODUCT_ID}' was not found."
    }
    assert invalid_response.status_code == 422


def test_inventory_set_repeat_replace_and_retrieve() -> None:
    client = create_test_client()
    product_id = create_product(client)["id"]
    positive_payload = {"on_hand_quantity": 100, "allocated_quantity": 35}

    first_response = client.put(
        f"/api/v1/products/{product_id}/inventory",
        json=positive_payload,
    )
    repeat_response = client.put(
        f"/api/v1/products/{product_id}/inventory",
        json=positive_payload,
    )
    zero_response = client.put(
        f"/api/v1/products/{product_id}/inventory",
        json={"on_hand_quantity": 5, "allocated_quantity": 5},
    )
    negative_response = client.put(
        f"/api/v1/products/{product_id}/inventory",
        json={"on_hand_quantity": 20, "allocated_quantity": 30},
    )
    get_response = client.get(f"/api/v1/products/{product_id}/inventory")

    assert first_response.status_code == 200
    assert first_response.json()["available_quantity"] == 65
    assert repeat_response.json() == first_response.json()
    assert zero_response.json()["available_quantity"] == 0
    assert negative_response.json()["available_quantity"] == -10
    assert get_response.status_code == 200
    assert get_response.json() == negative_response.json()


def test_inventory_validation_and_missing_states_are_safe_and_distinct() -> None:
    client = create_test_client()
    product_id = create_product(client)["id"]

    no_inventory_response = client.get(f"/api/v1/products/{product_id}/inventory")
    missing_get_response = client.get(
        f"/api/v1/products/{MISSING_PRODUCT_ID}/inventory"
    )
    missing_set_response = client.put(
        f"/api/v1/products/{MISSING_PRODUCT_ID}/inventory",
        json={"on_hand_quantity": 10, "allocated_quantity": 2},
    )
    negative_response = client.put(
        f"/api/v1/products/{product_id}/inventory",
        json={"on_hand_quantity": -1, "allocated_quantity": 0},
    )

    assert no_inventory_response.status_code == 404
    assert no_inventory_response.json() == {
        "detail": f"Inventory for product '{product_id}' was not found."
    }
    assert missing_get_response.status_code == 404
    assert missing_get_response.json() == {
        "detail": f"Product '{MISSING_PRODUCT_ID}' was not found."
    }
    assert missing_set_response.status_code == 404
    assert missing_set_response.json() == missing_get_response.json()
    assert negative_response.status_code == 422


def test_openapi_documents_all_five_operations_and_schemas() -> None:
    schema = create_test_client().get("/openapi.json").json()
    product_collection = schema["paths"]["/api/v1/products"]
    product_item = schema["paths"]["/api/v1/products/{product_id}"]
    inventory_item = schema["paths"]["/api/v1/products/{product_id}/inventory"]

    assert set(product_collection) == {"get", "post"}
    assert set(product_item) == {"get"}
    assert set(inventory_item) == {"get", "put"}
    assert set(product_collection["post"]["responses"]) >= {"201", "409", "422"}
    assert set(product_item["get"]["responses"]) >= {"200", "404", "422"}
    assert set(inventory_item["put"]["responses"]) >= {"200", "404", "422"}
    assert set(inventory_item["get"]["responses"]) >= {"200", "404", "422"}
    assert {
        "ProductCreateRequest",
        "ProductResponse",
        "InventorySetRequest",
        "InventoryResponse",
    } <= set(schema["components"]["schemas"])


def test_custom_business_prefix_and_unversioned_health() -> None:
    client = create_test_client("/supply/v2")

    assert client.get("/supply/v2/products").status_code == 200
    assert client.get("/api/v1/products").status_code == 404
    assert client.get("/supply/v2").status_code == 404
    assert client.get("/health").json() == {
        "status": "ok",
        "service": "opsmind-test-api",
        "environment": "test",
    }


def test_separate_applications_do_not_share_product_state() -> None:
    first_client = create_test_client()
    second_client = create_test_client()
    create_product(first_client)

    assert len(first_client.get("/api/v1/products").json()) == 1
    assert second_client.get("/api/v1/products").json() == []
