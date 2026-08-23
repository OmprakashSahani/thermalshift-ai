"""Tests for core ThermalShift domain validation."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from thermalshift.domain.models import (
    ScheduleDecision,
    Site,
    TemperatureObservation,
    ThermalAssessment,
    Workload,
)


def aware_time(hour: int = 12) -> datetime:
    return datetime(2024, 7, 15, hour, tzinfo=UTC)


def valid_site_data() -> dict[str, object]:
    return {
        "site_id": "modeled-site",
        "name": "Modeled Compute Site",
        "latitude": 39.0437,
        "longitude": -77.4875,
        "timezone": "America/New_York",
        "total_gpu_capacity": 64,
    }


def valid_workload_data() -> dict[str, object]:
    return {
        "workload_id": "workload-1",
        "name": "Flexible training run",
        "gpu_demand": 8,
        "duration_hours": 4,
        "release_time": aware_time(12),
        "deadline": aware_time(18),
        "priority": "medium",
        "eligible_site_ids": ["ashburn-va", "phoenix-az"],
    }


def test_valid_site() -> None:
    site = Site.model_validate(valid_site_data())

    assert site.site_id == "modeled-site"
    assert site.total_gpu_capacity == 64


@pytest.mark.parametrize(
    ("field", "value"),
    [("latitude", -90.1), ("latitude", 90.1), ("longitude", -180.1), ("longitude", 180.1)],
)
def test_invalid_coordinates(field: str, value: float) -> None:
    data = valid_site_data()
    data[field] = value

    with pytest.raises(ValidationError):
        Site.model_validate(data)


def test_nonexistent_timezone_is_rejected() -> None:
    data = valid_site_data()
    data["timezone"] = "America/Not_A_Real_Place"

    with pytest.raises(ValidationError, match="Unknown IANA timezone"):
        Site.model_validate(data)


@pytest.mark.parametrize("capacity", [0, -1])
def test_nonpositive_gpu_capacity_is_rejected(capacity: int) -> None:
    data = valid_site_data()
    data["total_gpu_capacity"] = capacity

    with pytest.raises(ValidationError):
        Site.model_validate(data)


def test_valid_workload() -> None:
    workload = Workload.model_validate(valid_workload_data())

    assert workload.gpu_demand == 8
    assert workload.eligible_site_ids == frozenset({"ashburn-va", "phoenix-az"})


@pytest.mark.parametrize("field", ["release_time", "deadline"])
def test_naive_workload_datetime_is_rejected(field: str) -> None:
    data = valid_workload_data()
    data[field] = datetime(2024, 7, 15, 12)

    with pytest.raises(ValidationError, match="timezone-aware"):
        Workload.model_validate(data)


@pytest.mark.parametrize("offset", [timedelta(0), timedelta(hours=-1)])
def test_deadline_not_after_release_is_rejected(offset: timedelta) -> None:
    data = valid_workload_data()
    data["deadline"] = aware_time(12) + offset

    with pytest.raises(ValidationError, match="deadline must be after release_time"):
        Workload.model_validate(data)


def test_infeasible_duration_window_remains_representable() -> None:
    data = valid_workload_data()
    data["duration_hours"] = 24
    data["deadline"] = aware_time(13)

    workload = Workload.model_validate(data)

    assert workload.duration_hours == 24


def test_duplicate_eligible_sites_are_deduplicated() -> None:
    data = valid_workload_data()
    data["eligible_site_ids"] = ["ashburn-va", "ashburn-va", "phoenix-az"]

    workload = Workload.model_validate(data)

    assert workload.eligible_site_ids == frozenset({"ashburn-va", "phoenix-az"})


def test_empty_eligible_sites_are_rejected() -> None:
    data = valid_workload_data()
    data["eligible_site_ids"] = []

    with pytest.raises(ValidationError):
        Workload.model_validate(data)


def test_temperature_observation_requires_aware_timestamp() -> None:
    with pytest.raises(ValidationError, match="timezone-aware"):
        TemperatureObservation(
            site_id="ashburn-va",
            timestamp=datetime(2024, 7, 15, 12),
            temperature_c=31.0,
            observation_type="historical",
        )


def test_temperature_observation_defaults_to_fortyguard_source() -> None:
    observation = TemperatureObservation(
        site_id="ashburn-va",
        timestamp=aware_time(),
        temperature_c=31.0,
        observation_type="historical",
    )

    assert observation.source == "fortyguard"


def valid_decision_data() -> dict[str, object]:
    return {
        "workload_id": "workload-1",
        "site_id": "ashburn-va",
        "start_time": aware_time(12),
        "end_time": aware_time(14),
        "thermal_exposure": 1.25,
        "thermal_stress_avg": 0.625,
        "deadline_satisfied": True,
        "capacity_satisfied": True,
        "scheduler_name": "test-scheduler",
    }


@pytest.mark.parametrize("end_time", [aware_time(12), aware_time(11)])
def test_schedule_decision_requires_end_after_start(end_time: datetime) -> None:
    data = valid_decision_data()
    data["end_time"] = end_time

    with pytest.raises(ValidationError, match="end_time must be after start_time"):
        ScheduleDecision.model_validate(data)


@pytest.mark.parametrize(
    ("field", "value"),
    [("thermal_exposure", -0.1), ("thermal_stress_avg", -0.1), ("thermal_stress_avg", 1.1)],
)
def test_schedule_thermal_fields_enforce_ranges(field: str, value: float) -> None:
    data = valid_decision_data()
    data[field] = value

    with pytest.raises(ValidationError):
        ScheduleDecision.model_validate(data)


@pytest.mark.parametrize("score", [-0.01, 1.01])
def test_assessment_score_enforces_range(score: float) -> None:
    with pytest.raises(ValidationError):
        ThermalAssessment(
            site_id="ashburn-va",
            timestamp=aware_time(),
            temperature_c=30.0,
            lower_reference_c=20.0,
            upper_reference_c=40.0,
            thermal_stress_score=score,
            risk_level="high",
        )
