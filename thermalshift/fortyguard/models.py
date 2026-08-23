"""Validated models for the known FortyGuard response contract."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FortyGuardModel(BaseModel):
    """Base model tolerant of additive fields in FortyGuard responses."""

    model_config = ConfigDict(extra="ignore")


class TemperatureStats(FortyGuardModel):
    """Summary statistics for temperatures in a heatmap result."""

    minimum: float
    maximum: float
    mean: float
    standard_deviation: float = Field(ge=0)


class DistributionSeries(FortyGuardModel):
    """Coordinates describing a temperature distribution series."""

    x_axis: list[float]
    y_axis: list[float]


class HeatmapStats(FortyGuardModel):
    """Statistical data returned for a completed heatmap."""

    temperature_stats: TemperatureStats
    overall_temperature_distribution: list[float]
    normal_temperature_distribution: DistributionSeries
    temperature_frequency: DistributionSeries


class HeatmapResult(FortyGuardModel):
    """Result payload returned for a completed heatmap activity."""

    map_data: dict[str, Any]
    stats_data: HeatmapStats


class ActivityStatus(FortyGuardModel):
    """Current state and optional result of a FortyGuard activity."""

    activity_id: str
    status: str
    result: HeatmapResult | None = None
