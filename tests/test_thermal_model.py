"""Tests for the calibrated thermal stress model."""

from datetime import UTC, datetime

import pytest

from thermalshift.domain.models import RiskLevel, TemperatureObservation
from thermalshift.thermal.model import (
    ThermalStressModel,
    calculate_thermal_exposure,
)

TIMESTAMP = datetime(2024, 7, 15, 14, tzinfo=UTC)


def observation(temperature_c: float) -> TemperatureObservation:
    return TemperatureObservation(
        site_id="ashburn-va",
        timestamp=TIMESTAMP,
        temperature_c=temperature_c,
        observation_type="historical",
    )


@pytest.mark.parametrize(
    ("temperature_c", "expected_score"),
    [(20.0, 0.0), (40.0, 1.0), (10.0, 0.0), (50.0, 1.0), (30.0, 0.5)],
)
def test_score_normalization_and_clamping(temperature_c: float, expected_score: float) -> None:
    model = ThermalStressModel(lower_reference_c=20.0, upper_reference_c=40.0)

    assessment = model.assess(observation(temperature_c))

    assert assessment.thermal_stress_score == pytest.approx(expected_score)


@pytest.mark.parametrize(
    ("score", "expected_risk"),
    [
        (0.0, RiskLevel.LOW),
        (0.249, RiskLevel.LOW),
        (0.25, RiskLevel.MODERATE),
        (0.499, RiskLevel.MODERATE),
        (0.5, RiskLevel.HIGH),
        (0.749, RiskLevel.HIGH),
        (0.75, RiskLevel.EXTREME),
        (1.0, RiskLevel.EXTREME),
    ],
)
def test_all_risk_bucket_boundaries(score: float, expected_risk: RiskLevel) -> None:
    model = ThermalStressModel(lower_reference_c=0.0, upper_reference_c=100.0)

    assert model.assess(observation(score * 100)).risk_level is expected_risk


@pytest.mark.parametrize(("lower", "upper"), [(20.0, 20.0), (21.0, 20.0)])
def test_invalid_calibration_is_rejected(lower: float, upper: float) -> None:
    with pytest.raises(ValueError, match="must be greater"):
        ThermalStressModel(lower_reference_c=lower, upper_reference_c=upper)


def test_assessment_preserves_raw_observation_fields() -> None:
    model = ThermalStressModel(lower_reference_c=20.0, upper_reference_c=40.0)
    raw = observation(31.5)

    assessment = model.assess(raw)

    assert assessment.site_id == raw.site_id
    assert assessment.timestamp == raw.timestamp
    assert assessment.temperature_c == raw.temperature_c


def test_exposure_calculation_in_thermal_stress_hours() -> None:
    exposure = calculate_thermal_exposure([0.25, 0.5, 1.0], interval_hours=0.5)

    assert exposure == pytest.approx(0.875)


def test_empty_scores_have_zero_exposure() -> None:
    assert calculate_thermal_exposure([], interval_hours=1.0) == 0.0


@pytest.mark.parametrize("interval_hours", [0.0, -0.5])
def test_invalid_interval_is_rejected(interval_hours: float) -> None:
    with pytest.raises(ValueError, match="greater than zero"):
        calculate_thermal_exposure([0.5], interval_hours=interval_hours)
