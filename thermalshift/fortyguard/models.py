"""Validated models for the known FortyGuard response contract."""

from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    field_validator,
    model_validator,
)


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


class NormalDistributionSeries(FortyGuardModel):
    """Normal-distribution coordinates with one observed null compatibility case."""

    x_axis: list[float]
    y_axis: list[StrictFloat | None]


class HeatmapStats(FortyGuardModel):
    """Statistical data returned for a completed heatmap."""

    temperature_stats: TemperatureStats
    overall_temperature_distribution: list[float]
    normal_temperature_distribution: NormalDistributionSeries
    temperature_frequency: DistributionSeries

    @field_validator("normal_temperature_distribution", mode="before")
    @classmethod
    def preserve_numeric_series_input(cls, value: Any) -> Any:
        """Keep existing direct numeric DistributionSeries construction compatible."""
        if isinstance(value, DistributionSeries):
            return value.model_dump()
        return value

    @model_validator(mode="after")
    def validate_degenerate_normal_distribution(self) -> "HeatmapStats":
        """Allow all-null normal density only for a strict zero-variance result."""
        distribution = self.normal_temperature_distribution
        stats = self.temperature_stats
        if not distribution.y_axis:
            if (
                stats.standard_deviation == 0
                and stats.minimum == stats.maximum
                and stats.minimum == stats.mean
            ):
                raise ValueError("zero-variance normal distribution must be non-empty")
            return self
        if not any(value is None for value in distribution.y_axis):
            return self
        if (
            not all(value is None for value in distribution.y_axis)
            or len(distribution.x_axis) != len(distribution.y_axis)
            or stats.standard_deviation != 0
            or stats.minimum != stats.maximum
            or stats.minimum != stats.mean
        ):
            raise ValueError(
                "null normal distribution requires matching non-empty axes and "
                "equal zero-variance temperature statistics"
            )
        return self


class HeatmapResult(FortyGuardModel):
    """Result payload returned for a completed heatmap activity."""

    map_data: dict[str, Any]
    stats_data: HeatmapStats


class ActivityStatus(FortyGuardModel):
    """Current state and optional result of a FortyGuard activity."""

    activity_id: str
    status: str
    result: HeatmapResult | None = None
