"""Product domain model and SKU normalization."""

from dataclasses import dataclass
from uuid import UUID


def normalize_sku(sku: str) -> str:
    """Return the canonical SKU used throughout product operations."""
    normalized_sku = sku.strip().upper()
    if not normalized_sku:
        raise ValueError("sku must not be empty")
    return normalized_sku


def _normalize_required_text(value: str, field_name: str) -> str:
    normalized_value = value.strip()
    if not normalized_value:
        raise ValueError(f"{field_name} must not be empty")
    return normalized_value


@dataclass(frozen=True, slots=True)
class Product:
    """Validated internal representation of a supply-chain product."""

    id: UUID
    sku: str
    name: str
    unit_of_measure: str
    lead_time_days: int
    is_active: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "sku", normalize_sku(self.sku))
        object.__setattr__(
            self,
            "name",
            _normalize_required_text(self.name, "name"),
        )
        object.__setattr__(
            self,
            "unit_of_measure",
            _normalize_required_text(self.unit_of_measure, "unit_of_measure"),
        )
        if self.lead_time_days < 0:
            raise ValueError("lead_time_days must be non-negative")
