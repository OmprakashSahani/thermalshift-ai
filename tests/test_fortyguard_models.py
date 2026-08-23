"""Tests for FortyGuard response models."""

import pytest
from pydantic import ValidationError

from thermalshift.fortyguard.models import ActivityStatus


def completed_data() -> dict[str, object]:
    return {
        "activity_id": "activity-123",
        "status": "Completed",
        "result": {
            "map_data": {},
            "stats_data": {
                "temperature_stats": {
                    "minimum": 36.6694,
                    "maximum": 36.8711,
                    "mean": 36.756608333333325,
                    "standard_deviation": 0.061370817144385616,
                },
                "overall_temperature_distribution": [36.6694, 36.7064, 36.75365],
                "normal_temperature_distribution": {
                    "x_axis": [36.6, 36.7, 36.8],
                    "y_axis": [1.0, 2.0, 1.0],
                },
                "temperature_frequency": {"x_axis": [37.0], "y_axis": [12.0]},
            },
        },
        "future_field": "ignored",
    }


def test_completed_result_parses() -> None:
    status = ActivityStatus.model_validate(completed_data())

    assert status.result is not None
    assert status.result.stats_data.temperature_stats.mean == pytest.approx(36.756608333333325)


def test_processing_without_result_parses() -> None:
    status = ActivityStatus.model_validate(
        {"activity_id": "activity-123", "status": "Processing"}
    )

    assert status.result is None


def test_negative_standard_deviation_is_rejected() -> None:
    payload = completed_data()
    payload["result"]["stats_data"]["temperature_stats"]["standard_deviation"] = -0.1  # type: ignore[index]

    with pytest.raises(ValidationError):
        ActivityStatus.model_validate(payload)
