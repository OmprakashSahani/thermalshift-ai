"""Pooled descriptive diagnostics for thermal model calibration."""

import math
import statistics
from collections.abc import Iterable
from dataclasses import dataclass

from thermalshift.domain.models import TemperatureObservation


class CalibrationError(ValueError):
    """Raised when pooled calibration diagnostics cannot be computed safely."""


@dataclass(frozen=True, slots=True)
class CalibrationDiagnostics:
    """Descriptive statistics for observations pooled across all sites."""

    count: int
    minimum_c: float
    maximum_c: float
    mean_c: float
    median_c: float
    p05_c: float
    p10_c: float
    p25_c: float
    p75_c: float
    p90_c: float
    p95_c: float


@dataclass(frozen=True, slots=True)
class ReferencePair:
    """One candidate shared lower/upper calibration pair."""

    label: str
    lower_reference_c: float
    upper_reference_c: float

    def __post_init__(self) -> None:
        if not self.upper_reference_c > self.lower_reference_c:
            raise CalibrationError("Candidate upper reference must be greater than lower reference")


def calculate_calibration_diagnostics(
    observations: Iterable[TemperatureObservation],
) -> CalibrationDiagnostics:
    """Calculate pooled statistics using linear `(n - 1) * q` quantiles."""
    values = sorted(observation.temperature_c for observation in observations)
    if not values:
        raise CalibrationError("At least one temperature observation is required")
    if not all(math.isfinite(value) for value in values):
        raise CalibrationError("Calibration temperatures must be finite")
    return CalibrationDiagnostics(
        count=len(values),
        minimum_c=values[0],
        maximum_c=values[-1],
        mean_c=statistics.fmean(values),
        median_c=statistics.median(values),
        p05_c=_linear_quantile(values, 0.05),
        p10_c=_linear_quantile(values, 0.10),
        p25_c=_linear_quantile(values, 0.25),
        p75_c=_linear_quantile(values, 0.75),
        p90_c=_linear_quantile(values, 0.90),
        p95_c=_linear_quantile(values, 0.95),
    )


def suggest_reference_pairs(
    diagnostics: CalibrationDiagnostics,
) -> tuple[ReferencePair, ReferencePair]:
    """Expose P05/P95 and P10/P90 candidates without selecting either one."""
    try:
        return (
            ReferencePair("P05/P95", diagnostics.p05_c, diagnostics.p95_c),
            ReferencePair("P10/P90", diagnostics.p10_c, diagnostics.p90_c),
        )
    except CalibrationError as exc:
        raise CalibrationError(
            "Pooled temperatures do not span a valid lower/upper reference pair"
        ) from exc


def _linear_quantile(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower_index = math.floor(position)
    upper_index = math.ceil(position)
    if lower_index == upper_index:
        return sorted_values[lower_index]
    fraction = position - lower_index
    return sorted_values[lower_index] + fraction * (
        sorted_values[upper_index] - sorted_values[lower_index]
    )
