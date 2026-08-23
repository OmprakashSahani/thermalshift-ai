"""Tests for pooled thermal calibration diagnostics."""

from datetime import UTC, datetime

import pytest

from thermalshift.domain.models import TemperatureObservation
from thermalshift.thermal.calibration import (
    CalibrationError,
    calculate_calibration_diagnostics,
    suggest_reference_pairs,
)


def observations(values: list[float]) -> list[TemperatureObservation]:
    return [
        TemperatureObservation(
            site_id=f"site-{index % 2}",
            timestamp=datetime(2024, 1, index + 1, tzinfo=UTC),
            temperature_c=value,
            observation_type="historical",
        )
        for index, value in enumerate(values)
    ]


def test_exact_basic_statistics_and_linear_quantiles() -> None:
    diagnostics = calculate_calibration_diagnostics(observations([0, 10, 20, 30, 40]))

    assert diagnostics.count == 5
    assert diagnostics.minimum_c == 0
    assert diagnostics.maximum_c == 40
    assert diagnostics.mean_c == 20
    assert diagnostics.median_c == 20
    assert diagnostics.p05_c == pytest.approx(2)
    assert diagnostics.p10_c == pytest.approx(4)
    assert diagnostics.p25_c == pytest.approx(10)
    assert diagnostics.p75_c == pytest.approx(30)
    assert diagnostics.p90_c == pytest.approx(36)
    assert diagnostics.p95_c == pytest.approx(38)


def test_observations_are_pooled_across_site_ids() -> None:
    diagnostics = calculate_calibration_diagnostics(observations([10, 20, 30, 40]))

    assert diagnostics.count == 4
    assert diagnostics.mean_c == 25


def test_candidate_reference_pairs_are_returned_without_selecting_one() -> None:
    diagnostics = calculate_calibration_diagnostics(observations([0, 10, 20, 30, 40]))

    pairs = suggest_reference_pairs(diagnostics)

    assert [(pair.label, pair.lower_reference_c, pair.upper_reference_c) for pair in pairs] == [
        ("P05/P95", pytest.approx(2), pytest.approx(38)),
        ("P10/P90", pytest.approx(4), pytest.approx(36)),
    ]


def test_empty_input_is_rejected() -> None:
    with pytest.raises(CalibrationError, match="At least one"):
        calculate_calibration_diagnostics([])


def test_nonfinite_temperature_is_rejected_defensively() -> None:
    invalid = TemperatureObservation.model_construct(
        site_id="site-1",
        timestamp=datetime(2024, 1, 1, tzinfo=UTC),
        temperature_c=float("nan"),
        source="fortyguard",
        observation_type="historical",
    )

    with pytest.raises(CalibrationError, match="finite"):
        calculate_calibration_diagnostics([invalid])


def test_constant_temperature_does_not_produce_invalid_reference_pairs() -> None:
    diagnostics = calculate_calibration_diagnostics(observations([25, 25, 25]))

    with pytest.raises(CalibrationError, match="do not span"):
        suggest_reference_pairs(diagnostics)


def test_quantile_ordering_properties() -> None:
    diagnostics = calculate_calibration_diagnostics(observations([8, 1, 13, 5, 3, 21]))

    assert (
        diagnostics.p05_c
        <= diagnostics.p10_c
        <= diagnostics.p25_c
        <= diagnostics.median_c
        <= diagnostics.p75_c
        <= diagnostics.p90_c
        <= diagnostics.p95_c
    )
