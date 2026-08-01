"""Public product API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProductCreateRequest(BaseModel):
    """Fields accepted when creating a product."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sku": "SENSOR-001",
                "name": "Temperature Sensor",
                "unit_of_measure": "each",
                "lead_time_days": 14,
                "is_active": True,
            }
        }
    )

    sku: str = Field(
        min_length=1,
        description="Business SKU; surrounding whitespace is removed and letters uppercase.",
    )
    name: str = Field(min_length=1, description="Human-readable product name.")
    unit_of_measure: str = Field(
        min_length=1,
        description="Unit used to count this product, such as each or case.",
    )
    lead_time_days: int = Field(
        ge=0,
        description="Non-negative replenishment lead time in calendar days.",
    )
    is_active: bool = Field(
        default=True,
        description="Whether the product is currently active.",
    )


class ProductResponse(BaseModel):
    """Public representation of a stored product."""

    id: UUID = Field(description="Server-generated product identifier.")
    sku: str = Field(description="Canonical normalized product SKU.")
    name: str = Field(description="Trimmed human-readable product name.")
    unit_of_measure: str = Field(description="Trimmed product counting unit.")
    lead_time_days: int = Field(description="Replenishment lead time in days.")
    is_active: bool = Field(description="Whether the product is active.")
