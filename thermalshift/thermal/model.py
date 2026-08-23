"""Linear calibrated thermal stress model and exposure calculation."""

from collections.abc import Iterable
from dataclasses import dataclass

from thermalshift.domain.models import RiskLevel, TemperatureObservation, ThermalAssessment


@dataclass(frozen=True, slots=True)
class ThermalStressModel:
    """Normalize ambient temperature between two calibration references."""

    lower_reference_c: float
    upper_reference_c: float

    def __post_init__(self) -> None:
        if not self.upper_reference_c > self.lower_reference_c:
            raise ValueError("upper_reference_c must be greater than lower_reference_c")

    def assess(self, observation: TemperatureObservation) -> ThermalAssessment:
        """Convert a raw observation into a modeled thermal assessment."""
        raw_score = (observation.temperature_c - self.lower_reference_c) / (
            self.upper_reference_c - self.lower_reference_c
        )
        score = min(max(raw_score, 0.0), 1.0)
        return ThermalAssessment(
            site_id=observation.site_id,
            timestamp=observation.timestamp,
            temperature_c=observation.temperature_c,
            lower_reference_c=self.lower_reference_c,
            upper_reference_c=self.upper_reference_c,
            thermal_stress_score=score,
            risk_level=_risk_level(score),
        )


def calculate_thermal_exposure(
    stress_scores: Iterable[float], *, interval_hours: float
) -> float:
    """Calculate modeled thermal exposure in thermal stress-hours."""
    if not interval_hours > 0:
        raise ValueError("interval_hours must be greater than zero")
    return sum(stress_scores) * interval_hours


def _risk_level(score: float) -> RiskLevel:
    if score < 0.25:
        return RiskLevel.LOW
    if score < 0.50:
        return RiskLevel.MODERATE
    if score < 0.75:
        return RiskLevel.HIGH
    return RiskLevel.EXTREME
