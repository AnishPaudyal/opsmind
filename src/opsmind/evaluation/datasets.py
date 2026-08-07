"""Deterministic synthetic demand series for Phase 4 forecast evaluation."""

from dataclasses import dataclass
from datetime import date, timedelta
from uuid import UUID

from opsmind.domain.demand import DemandObservation

DATASET_VERSION = "phase4-synthetic-v1"
DATASET_START_DATE = date(2026, 1, 1)

_STABLE_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000001")
_UPWARD_TREND_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000002")
_DOWNWARD_TREND_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000003")
_WEEKLY_SEASONAL_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000004")
_INTERMITTENT_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000005")
_ALL_ZERO_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000006")
_MISSING_DATES_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000007")
_SHORT_HISTORY_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000008")
_LEVEL_SHIFT_PRODUCT_ID = UUID("51000000-0000-0000-0000-000000000009")


@dataclass(frozen=True, slots=True)
class EvaluationSeries:
    """One named immutable synthetic demand series."""

    pattern_name: str
    product_id: UUID
    observations: tuple[DemandObservation, ...]


def _build_series(
    *,
    pattern_name: str,
    product_id: UUID,
    quantities: tuple[int, ...],
    omitted_offsets: frozenset[int] = frozenset(),
) -> EvaluationSeries:
    observations = tuple(
        DemandObservation(
            product_id,
            DATASET_START_DATE + timedelta(days=offset),
            quantity,
        )
        for offset, quantity in enumerate(quantities)
        if offset not in omitted_offsets
    )
    return EvaluationSeries(
        pattern_name=pattern_name,
        product_id=product_id,
        observations=observations,
    )


def build_phase4_dataset() -> tuple[EvaluationSeries, ...]:
    """Return the complete deterministic synthetic Phase 4 dataset."""
    weekly_pattern = (5, 8, 11, 14, 11, 8, 5)
    intermittent_pattern = (0, 0, 0, 14, 0, 0, 7)

    series = (
        _build_series(
            pattern_name="stable",
            product_id=_STABLE_PRODUCT_ID,
            quantities=(10,) * 35,
        ),
        _build_series(
            pattern_name="upward_trend",
            product_id=_UPWARD_TREND_PRODUCT_ID,
            quantities=tuple(5 + offset // 2 for offset in range(35)),
        ),
        _build_series(
            pattern_name="downward_trend",
            product_id=_DOWNWARD_TREND_PRODUCT_ID,
            quantities=tuple(max(1, 25 - offset // 2) for offset in range(35)),
        ),
        _build_series(
            pattern_name="weekly_seasonal",
            product_id=_WEEKLY_SEASONAL_PRODUCT_ID,
            quantities=weekly_pattern * 5,
        ),
        _build_series(
            pattern_name="intermittent",
            product_id=_INTERMITTENT_PRODUCT_ID,
            quantities=intermittent_pattern * 5,
        ),
        _build_series(
            pattern_name="all_zero",
            product_id=_ALL_ZERO_PRODUCT_ID,
            quantities=(0,) * 35,
        ),
        _build_series(
            pattern_name="missing_calendar_dates",
            product_id=_MISSING_DATES_PRODUCT_ID,
            quantities=(9,) * 35,
            omitted_offsets=frozenset({12, 24}),
        ),
        _build_series(
            pattern_name="short_history",
            product_id=_SHORT_HISTORY_PRODUCT_ID,
            quantities=(8,) * 10,
        ),
        _build_series(
            pattern_name="abrupt_upward_level_shift",
            product_id=_LEVEL_SHIFT_PRODUCT_ID,
            quantities=(5,) * 21 + (20,) * 14,
        ),
    )
    return tuple(sorted(series, key=lambda item: item.pattern_name))
