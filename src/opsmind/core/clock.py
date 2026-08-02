"""Narrow clock boundary for deterministic workflow timestamps."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Supply the current timezone-aware UTC datetime."""

    def now(self) -> datetime:
        """Return the current instant."""
        ...


@dataclass(frozen=True, slots=True)
class SystemClock:
    """Production clock backed by the system UTC time."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC datetime."""
        return datetime.now(UTC)
