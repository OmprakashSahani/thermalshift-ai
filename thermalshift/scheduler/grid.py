"""Validated one-hour modeled thermal stress grid."""

import math
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


class ThermalGridError(ValueError):
    """Raised when hourly thermal grid data is invalid."""


@dataclass(frozen=True, slots=True)
class ThermalGridEntry:
    """One site/hour modeled thermal stress value."""

    site_id: str
    timestamp: datetime
    score: float


@dataclass(frozen=True, slots=True)
class PlacementThermalMetrics:
    """Thermal annotations for an hourly candidate placement."""

    scores: tuple[float, ...]
    average_stress: float
    exposure_stress_hours: float


class ThermalGrid:
    """Deterministic UTC-normalized lookup of hourly thermal stress scores."""

    interval_hours = 1

    def __init__(self, entries: Iterable[ThermalGridEntry]) -> None:
        values: dict[tuple[str, datetime], float] = {}
        for entry in entries:
            site_id = entry.site_id.strip()
            if not site_id:
                raise ThermalGridError("site_id must not be blank")
            timestamp = normalize_hour(entry.timestamp)
            if not math.isfinite(entry.score) or not 0 <= entry.score <= 1:
                raise ThermalGridError("thermal stress score must be finite and in [0, 1]")
            key = (site_id, timestamp)
            if key in values:
                raise ThermalGridError("duplicate normalized site/timestamp thermal grid entry")
            values[key] = entry.score
        self._values = values

    def get_score(self, site_id: str, timestamp: datetime) -> float:
        """Return one score using a timezone-aware hour normalized to UTC."""
        return self._values[(site_id, normalize_hour(timestamp))]

    def available_timestamps(self, site_id: str | None = None) -> tuple[datetime, ...]:
        """Return sorted UTC hours available globally or for one site."""
        return tuple(
            sorted(
                {
                    timestamp
                    for (entry_site_id, timestamp) in self._values
                    if site_id is None or entry_site_id == site_id
                }
            )
        )

    def placement_metrics(
        self, site_id: str, start_time: datetime, duration_hours: int
    ) -> PlacementThermalMetrics | None:
        """Return hourly scores, average, and thermal stress-hours, or None if incomplete."""
        start_utc = normalize_hour(start_time)
        timestamps = tuple(start_utc + timedelta(hours=offset) for offset in range(duration_hours))
        try:
            scores = tuple(self._values[(site_id, timestamp)] for timestamp in timestamps)
        except KeyError:
            return None
        exposure = sum(scores) * self.interval_hours
        return PlacementThermalMetrics(
            scores=scores,
            average_stress=exposure / duration_hours,
            exposure_stress_hours=exposure,
        )


def normalize_hour(timestamp: datetime) -> datetime:
    """Validate an exact aware hour and normalize it to UTC."""
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ThermalGridError("thermal grid timestamp must be timezone-aware")
    if timestamp.minute or timestamp.second or timestamp.microsecond:
        raise ThermalGridError("thermal grid timestamp must be on an exact hour boundary")
    return timestamp.astimezone(UTC)
