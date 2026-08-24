"""Tests for FortyGuard response models."""

import pytest
from pydantic import ValidationError

from thermalshift.fortyguard.models import ActivityStatus, DistributionSeries


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


def degenerate_null_data() -> dict[str, object]:
    payload = completed_data()
    stats = payload["result"]["stats_data"]  # type: ignore[index]
    stats["temperature_stats"] = {  # type: ignore[index]
        "minimum": 6.21,
        "maximum": 6.21,
        "mean": 6.21,
        "standard_deviation": 0.0,
    }
    stats["normal_temperature_distribution"] = {  # type: ignore[index]
        "x_axis": [6.21, 6.21, 6.21],
        "y_axis": [None, None, None],
    }
    return payload


def test_zero_variance_all_null_normal_distribution_validates_without_conversion() -> None:
    status = ActivityStatus.model_validate(degenerate_null_data())

    assert status.result is not None
    assert status.result.stats_data.normal_temperature_distribution.y_axis == [
        None,
        None,
        None,
    ]
    assert status.result.stats_data.temperature_stats.mean == 6.21


@pytest.mark.parametrize(
    ("y_axis", "stats_update", "x_axis"),
    [
        ([None, 1.0], {}, [1.0, 2.0]),
        ([None, None], {"standard_deviation": 0.1}, [1.0, 2.0]),
        ([None, None], {"maximum": 7.0}, [1.0, 2.0]),
        ([None, None], {"mean": 7.0}, [1.0, 2.0]),
        ([None, None], {}, [1.0]),
        ([], {}, []),
    ],
)
def test_invalid_null_normal_distribution_is_rejected(
    y_axis: list[float | None], stats_update: dict[str, float], x_axis: list[float]
) -> None:
    payload = degenerate_null_data()
    stats = payload["result"]["stats_data"]  # type: ignore[index]
    stats["temperature_stats"].update(stats_update)  # type: ignore[index,union-attr]
    stats["normal_temperature_distribution"] = {  # type: ignore[index]
        "x_axis": x_axis,
        "y_axis": y_axis,
    }

    with pytest.raises(ValidationError):
        ActivityStatus.model_validate(payload)


@pytest.mark.parametrize("invalid", ["secret", True, {}, []])
def test_normal_distribution_rejects_non_numeric_non_null_values(invalid: object) -> None:
    payload = completed_data()
    distribution = payload["result"]["stats_data"][  # type: ignore[index]
        "normal_temperature_distribution"
    ]
    distribution["y_axis"] = [invalid]  # type: ignore[index]

    with pytest.raises(ValidationError):
        ActivityStatus.model_validate(payload)


def test_generic_and_temperature_frequency_distributions_remain_numeric() -> None:
    with pytest.raises(ValidationError):
        DistributionSeries.model_validate({"x_axis": [1.0], "y_axis": [None]})

    payload = completed_data()
    payload["result"]["stats_data"]["temperature_frequency"]["y_axis"] = [None]  # type: ignore[index]
    with pytest.raises(ValidationError):
        ActivityStatus.model_validate(payload)
