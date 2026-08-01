"""Public inventory API schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InventorySetRequest(BaseModel):
    """Authoritative quantities accepted for an inventory position."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "on_hand_quantity": 100,
                "allocated_quantity": 35,
            }
        }
    )

    on_hand_quantity: int = Field(
        ge=0,
        description="Physical quantity currently on hand.",
    )
    allocated_quantity: int = Field(
        ge=0,
        description="Quantity already allocated to demand.",
    )


class InventoryResponse(BaseModel):
    """Public inventory position with calculated availability."""

    product_id: UUID = Field(description="Product owning this inventory position.")
    on_hand_quantity: int = Field(description="Physical quantity currently on hand.")
    allocated_quantity: int = Field(description="Quantity allocated to demand.")
    available_quantity: int = Field(
        description="On-hand quantity minus allocated quantity; may be negative.",
    )
