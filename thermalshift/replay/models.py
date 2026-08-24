"""Immutable models for offline FortyGuard historical replay."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from thermalshift.domain.models import TemperatureObservation
from thermalshift.thermal.calibration import CalibrationDiagnostics


@dataclass(frozen=True, slots=True)
class HistoricalReplayWindow:
    """A predeclared sequence of consecutive one-hour replay slots."""

    window_id: str
    description: str
    start_utc: datetime
    slot_count: int
    interval_hours: int = 1

    def __post_init__(self) -> None:
        if not self.window_id.strip() or not self.description.strip():
            raise ValueError("replay window ID and description must not be blank")
        if self.start_utc.tzinfo is not UTC:
            raise ValueError("replay window start_utc must use the UTC timezone")
        if self.slot_count <= 0:
            raise ValueError("replay window slot_count must be positive")
        if self.interval_hours != 1:
            raise ValueError("replay window interval_hours must be exactly 1")

    @property
    def instants(self) -> tuple[datetime, ...]:
        """Return all consecutive requested UTC instants."""
        return tuple(
            self.start_utc + timedelta(hours=offset)
            for offset in range(self.slot_count)
        )


@dataclass(frozen=True, slots=True)
class ReplayPlanEntry:
    """Safe audit metadata for one cache-backed historical request."""

    request_number: int
    window_id: str
    site_id: str
    requested_utc: datetime
    site_local_time: datetime
    cache_key: str
    cache_hit: bool


@dataclass(frozen=True, slots=True)
class ReplayCollectionPlan:
    """Ordered cache state for one replay window."""

    window: HistoricalReplayWindow
    entries: tuple[ReplayPlanEntry, ...]

    @property
    def cache_hit_count(self) -> int:
        """Return the number of already cached requests."""
        return sum(entry.cache_hit for entry in self.entries)

    @property
    def missing_count(self) -> int:
        """Return the number of requests still absent from cache."""
        return len(self.entries) - self.cache_hit_count


@dataclass(frozen=True, slots=True)
class CalibrationStatus:
    """Completeness and pooled diagnostics for the fixed calibration sample."""

    expected_count: int
    observations: tuple[TemperatureObservation, ...]
    missing_entries: tuple[ReplayPlanEntry, ...]
    diagnostics: CalibrationDiagnostics | None
    lower_reference_c: float | None
    upper_reference_c: float | None
    reference_error: str | None = None

    @property
    def available_count(self) -> int:
        """Return the number of successful cached calibration observations."""
        return len(self.observations)

    @property
    def complete(self) -> bool:
        """Return whether all intended calibration observations are available."""
        return self.available_count == self.expected_count and not self.missing_entries

    @property
    def official_ready(self) -> bool:
        """Return whether complete data also supplies a valid frozen reference pair."""
        return (
            self.complete
            and self.lower_reference_c is not None
            and self.upper_reference_c is not None
            and self.reference_error is None
        )


class ReplayDataIncompleteError(RuntimeError):
    """Raised when cache-only replay inputs are incomplete or invalid."""

    def __init__(
        self,
        data_kind: str,
        expected_count: int,
        available_count: int,
        missing_entries: tuple[ReplayPlanEntry, ...] = (),
        *,
        detail: str | None = None,
    ) -> None:
        self.data_kind = data_kind
        self.expected_count = expected_count
        self.available_count = available_count
        self.missing_entries = missing_entries
        message = (
            f"{data_kind} data incomplete: {available_count}/{expected_count} cached"
        )
        if detail:
            message = f"{message}; {detail}"
        super().__init__(message)
