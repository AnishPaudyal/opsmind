"""Tests for product domain rules."""

from uuid import UUID

import pytest

from opsmind.domain.product import Product, normalize_sku

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")


def create_product(
    product_id: UUID = PRODUCT_ID,
    sku: str = "SENSOR-001",
    name: str = "Temperature Sensor",
    unit_of_measure: str = "each",
    lead_time_days: int = 14,
    *,
    is_active: bool = True,
) -> Product:
    """Create a product with valid defaults and selected values."""
    return Product(
        id=product_id,
        sku=sku,
        name=name,
        unit_of_measure=unit_of_measure,
        lead_time_days=lead_time_days,
        is_active=is_active,
    )


def test_normalize_sku_trims_and_uppercases() -> None:
    assert normalize_sku(" sensor-001 ") == "SENSOR-001"


def test_normalize_sku_treats_case_and_whitespace_as_equivalent() -> None:
    assert normalize_sku("Sensor-001") == normalize_sku("  sensor-001 ")


@pytest.mark.parametrize("sku", ["", "   "])
def test_normalize_sku_rejects_empty_values(sku: str) -> None:
    with pytest.raises(ValueError, match=r"^sku must not be empty$"):
        normalize_sku(sku)


def test_product_normalizes_sku_and_trims_text() -> None:
    product = create_product(
        sku=" sensor-001 ",
        name=" Temperature Sensor ",
        unit_of_measure=" each ",
    )

    assert product.sku == "SENSOR-001"
    assert product.name == "Temperature Sensor"
    assert product.unit_of_measure == "each"


@pytest.mark.parametrize("name", ["", "   "])
def test_product_rejects_empty_name(name: str) -> None:
    with pytest.raises(ValueError, match=r"^name must not be empty$"):
        create_product(name=name)


@pytest.mark.parametrize("unit_of_measure", ["", "   "])
def test_product_rejects_empty_unit_of_measure(unit_of_measure: str) -> None:
    with pytest.raises(ValueError, match=r"^unit_of_measure must not be empty$"):
        create_product(unit_of_measure=unit_of_measure)


def test_product_rejects_negative_lead_time() -> None:
    with pytest.raises(ValueError, match=r"^lead_time_days must be non-negative$"):
        create_product(lead_time_days=-1)
