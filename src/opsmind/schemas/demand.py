"""Public demand-history API schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DemandObservationCreate(BaseModel):
    """One daily demand value accepted for batch ingestion."""

    demand_date: date = Field(
        description="Calendar date for this daily demand observation.",
        examples=["2026-07-01"],
    )
    quantity: int = Field(
        ge=0,
        strict=True,
        description="Non-negative observed demand; zero is valid.",
        examples=[12],
    )


class DemandBatchCreate(BaseModel):
    """Nonempty batch of daily demand observations for one product."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "observations": [
                    {"demand_date": "2026-07-02", "quantity": 18},
                    {"demand_date": "2026-07-01", "quantity": 12},
                ]
            }
        }
    )

    observations: list[DemandObservationCreate] = Field(
        min_length=1,
        description="Daily observations stored atomically as one batch.",
    )


class DemandObservationResponse(BaseModel):
    """Stored daily product demand returned by the API."""

    product_id: UUID = Field(description="Product owning the demand observation.")
    demand_date: date = Field(description="Observation calendar date.")
    quantity: int = Field(description="Observed non-negative daily demand.")
