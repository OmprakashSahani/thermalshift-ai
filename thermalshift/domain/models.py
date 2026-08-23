"""Core validated domain models for ThermalShift."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
AwareDatetime = Annotated[datetime, Field(strict=True)]


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


class DomainModel(BaseModel):
    """Immutable base for deterministic ThermalShift domain values."""

    model_config = ConfigDict(frozen=True, extra="forbid", allow_inf_nan=False)


class WorkloadPriority(StrEnum):
    """Supported workload priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ObservationType(StrEnum):
    """Time relationship of a raw temperature observation."""

    HISTORICAL = "historical"
    CURRENT = "current"
    FORECAST = "forecast"


class RiskLevel(StrEnum):
    """Interpretive bucket for a modeled thermal stress score."""

    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class Site(DomainModel):
    """A modeled compute site used for scheduling experiments."""

    site_id: NonEmptyString
    name: NonEmptyString
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: NonEmptyString
    total_gpu_capacity: int = Field(gt=0)

    @model_validator(mode="after")
    def validate_timezone(self) -> Self:
        """Require a timezone present in the system IANA database."""
        try:
            ZoneInfo(self.timezone)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Unknown IANA timezone: {self.timezone}") from exc
        return self


class Workload(DomainModel):
    """A flexible GPU workload, including intentionally infeasible cases."""

    workload_id: NonEmptyString
    name: NonEmptyString
    gpu_demand: int = Field(gt=0)
    duration_hours: int = Field(gt=0)
    release_time: AwareDatetime
    deadline: AwareDatetime
    priority: WorkloadPriority
    eligible_site_ids: frozenset[NonEmptyString] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        """Require aware datetimes in chronological order."""
        _require_aware(self.release_time, "release_time")
        _require_aware(self.deadline, "deadline")
        if self.deadline <= self.release_time:
            raise ValueError("deadline must be after release_time")
        return self


class TemperatureObservation(DomainModel):
    """Raw environmental temperature input, separate from derived assessment."""

    site_id: NonEmptyString
    timestamp: AwareDatetime
    temperature_c: float
    source: Literal["fortyguard"] = "fortyguard"
    observation_type: ObservationType

    @model_validator(mode="after")
    def validate_timestamp(self) -> Self:
        """Require an aware observation timestamp."""
        _require_aware(self.timestamp, "timestamp")
        return self


class ThermalAssessment(DomainModel):
    """Derived modeled thermal decision metric for one observation."""

    site_id: NonEmptyString
    timestamp: AwareDatetime
    temperature_c: float
    lower_reference_c: float
    upper_reference_c: float
    thermal_stress_score: float = Field(ge=0, le=1)
    risk_level: RiskLevel

    @model_validator(mode="after")
    def validate_assessment(self) -> Self:
        """Require an aware timestamp and ordered calibration references."""
        _require_aware(self.timestamp, "timestamp")
        if not self.upper_reference_c > self.lower_reference_c:
            raise ValueError("upper_reference_c must be greater than lower_reference_c")
        return self


class ScheduleDecision(DomainModel):
    """Validated output record produced by a scheduler."""

    workload_id: NonEmptyString
    site_id: NonEmptyString
    start_time: AwareDatetime
    end_time: AwareDatetime
    thermal_exposure: float = Field(ge=0)
    thermal_stress_avg: float = Field(ge=0, le=1)
    deadline_satisfied: bool
    capacity_satisfied: bool
    scheduler_name: NonEmptyString
    decision_reason: str | None = None

    @model_validator(mode="after")
    def validate_times(self) -> Self:
        """Require aware decision times in chronological order."""
        _require_aware(self.start_time, "start_time")
        _require_aware(self.end_time, "end_time")
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self
