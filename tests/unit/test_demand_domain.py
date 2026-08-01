"""Tests for pure demand-observation domain behavior."""

from datetime import date
from typing import cast
from uuid import UUID

import pytest

from opsmind.domain.demand import (
    DemandObservation,
    validate_demand_batch,
    validate_demand_date_range,
)
from opsmind.domain.errors import DuplicateDemandDateError

PRODUCT_ID = UUID("00000000-0000-0000-0000-000000000001")


def observation(demand_date: date, quantity: int = 1) -> DemandObservation:
    """Create one demand observation for the test product."""
    return DemandObservation(PRODUCT_ID, demand_date, quantity)


def test_positive_quantity_and_typed_date_are_preserved() -> None:
    demand_date = date(2026, 7, 1)
    item = observation(demand_date, 12)

    assert item.demand_date is demand_date
    assert item.quantity == 12


def test_zero_quantity_is_valid() -> None:
    assert observation(date(2026, 7, 1), 0).quantity == 0


def test_product_id_and_demand_date_must_use_required_domain_types() -> None:
    with pytest.raises(TypeError, match=r"^product_id must be a UUID$"):
        DemandObservation(cast(UUID, None), date(2026, 7, 1), 1)
    with pytest.raises(TypeError, match=r"^demand_date must be a date$"):
        DemandObservation(PRODUCT_ID, cast(date, None), 1)


def test_negative_quantity_is_rejected() -> None:
    with pytest.raises(ValueError, match=r"^quantity must be non-negative$"):
        observation(date(2026, 7, 1), -1)


@pytest.mark.parametrize("quantity", [1.5, "1", True])
def test_quantity_must_be_an_integer(quantity: object) -> None:
    with pytest.raises(TypeError, match=r"^quantity must be an integer$"):
        DemandObservation(PRODUCT_ID, date(2026, 7, 1), cast(int, quantity))


def test_batch_rejects_duplicate_dates_for_one_product() -> None:
    demand_date = date(2026, 7, 1)

    with pytest.raises(DuplicateDemandDateError) as error:
        validate_demand_batch(
            PRODUCT_ID,
            (observation(demand_date, 12), observation(demand_date, 18)),
        )

    assert error.value.product_id == PRODUCT_ID
    assert error.value.demand_date == demand_date


def test_batch_returns_unsorted_input_chronologically() -> None:
    observations = (
        observation(date(2026, 7, 3), 9),
        observation(date(2026, 7, 1), 12),
        observation(date(2026, 7, 2), 18),
    )

    chronological = validate_demand_batch(PRODUCT_ID, observations)

    assert [item.demand_date.day for item in chronological] == [1, 2, 3]
    assert chronological is not observations


def test_batch_rejects_observation_for_another_product() -> None:
    other_product_id = UUID("00000000-0000-0000-0000-000000000002")

    with pytest.raises(
        ValueError,
        match=r"^observation product_id must match batch product_id$",
    ):
        validate_demand_batch(
            PRODUCT_ID,
            (DemandObservation(other_product_id, date(2026, 7, 1), 1),),
        )


def test_empty_batch_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=r"^at least one demand observation is required$",
    ):
        validate_demand_batch(PRODUCT_ID, ())


@pytest.mark.parametrize(
    ("start_date", "end_date"),
    [
        (None, None),
        (date(2026, 7, 1), None),
        (None, date(2026, 7, 2)),
        (date(2026, 7, 1), date(2026, 7, 1)),
        (date(2026, 7, 1), date(2026, 7, 2)),
    ],
)
def test_valid_date_ranges(
    start_date: date | None,
    end_date: date | None,
) -> None:
    validate_demand_date_range(start_date, end_date)


def test_reversed_date_range_is_rejected() -> None:
    with pytest.raises(
        ValueError,
        match=r"^start_date must be on or before end_date$",
    ):
        validate_demand_date_range(date(2026, 7, 2), date(2026, 7, 1))
