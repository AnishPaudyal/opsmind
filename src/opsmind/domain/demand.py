"""Demand-observation domain model and validation rules."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from opsmind.domain.errors import DuplicateDemandDateError


@dataclass(frozen=True, slots=True)
class DemandObservation:
    """One product's observed demand for one calendar date."""

    product_id: UUID
    demand_date: date
    quantity: int

    def __post_init__(self) -> None:
        if not isinstance(self.product_id, UUID):
            raise TypeError("product_id must be a UUID")
        if not isinstance(self.demand_date, date):
            raise TypeError("demand_date must be a date")
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            raise TypeError("quantity must be an integer")
        if self.quantity < 0:
            raise ValueError("quantity must be non-negative")


def validate_demand_batch(
    product_id: UUID,
    observations: tuple[DemandObservation, ...],
) -> tuple[DemandObservation, ...]:
    """Validate one product batch and return chronological immutable output."""
    if not observations:
        raise ValueError("at least one demand observation is required")

    dates_seen: set[date] = set()
    for observation in observations:
        if observation.product_id != product_id:
            raise ValueError("observation product_id must match batch product_id")
        if observation.demand_date in dates_seen:
            raise DuplicateDemandDateError(product_id, observation.demand_date)
        dates_seen.add(observation.demand_date)

    return tuple(sorted(observations, key=lambda item: item.demand_date))


def validate_demand_date_range(
    start_date: date | None,
    end_date: date | None,
) -> None:
    """Validate an optional inclusive demand-history date range."""
    if start_date is not None and end_date is not None and start_date > end_date:
        raise ValueError("start_date must be on or before end_date")
