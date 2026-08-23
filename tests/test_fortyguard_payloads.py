"""Tests for deterministic historical FortyGuard payload construction."""

import math
from datetime import UTC, datetime

import pytest

from thermalshift.domain.models import Site
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.payloads import (
    FortyGuardPayloadError,
    build_historical_heatmap_payload,
)


def ring_for(site: Site, timestamp: datetime) -> list[list[float]]:
    payload = build_historical_heatmap_payload(site, timestamp)
    return payload["polygon_aoi"]["features"][0]["geometry"]["coordinates"][0]


def test_payload_is_deterministic() -> None:
    site = get_default_sites()[0]
    timestamp = datetime(2024, 7, 15, 18, tzinfo=UTC)

    assert build_historical_heatmap_payload(site, timestamp) == build_historical_heatmap_payload(
        site, timestamp
    )


def test_polygon_is_closed_and_centered_on_site() -> None:
    site = get_default_sites()[0]
    ring = ring_for(site, datetime(2024, 7, 15, 18, tzinfo=UTC))

    assert ring[0] == ring[-1]
    assert (ring[0][0] + ring[1][0]) / 2 == pytest.approx(site.longitude)
    assert (ring[0][1] + ring[2][1]) / 2 == pytest.approx(site.latitude)


def test_meter_scale_is_consistent_across_latitudes() -> None:
    timestamp = datetime(2024, 7, 15, 18, tzinfo=UTC)
    widths_m = []
    for site in (get_default_sites()[0], get_default_sites()[1]):
        ring = ring_for(site, timestamp)
        longitude_width = ring[1][0] - ring[0][0]
        widths_m.append(longitude_width * 111_320 * math.cos(math.radians(site.latitude)))

    assert widths_m == pytest.approx([400.0, 400.0])


def test_timestamp_is_converted_to_site_timezone() -> None:
    phoenix = get_default_sites()[1]

    payload = build_historical_heatmap_payload(
        phoenix, datetime(2024, 7, 15, 6, 30, tzinfo=UTC)
    )

    assert payload["date_time"]["start_date"] == "2024-07-14"
    assert payload["date_time"]["start_time"] == "23:30"


@pytest.mark.parametrize("granularity", [60, 80, 100])
def test_valid_granularity_is_accepted(granularity: int) -> None:
    payload = build_historical_heatmap_payload(
        get_default_sites()[0],
        datetime(2024, 7, 15, tzinfo=UTC),
        granularity=granularity,
    )

    assert payload["granularity"] == granularity


@pytest.mark.parametrize("granularity", [0, 50, 101])
def test_invalid_granularity_is_rejected(granularity: int) -> None:
    with pytest.raises(FortyGuardPayloadError, match="granularity"):
        build_historical_heatmap_payload(
            get_default_sites()[0],
            datetime(2024, 7, 15, tzinfo=UTC),
            granularity=granularity,
        )


@pytest.mark.parametrize("half_size", [0.0, -1.0, float("inf")])
def test_invalid_aoi_size_is_rejected(half_size: float) -> None:
    with pytest.raises(FortyGuardPayloadError, match="half-size"):
        build_historical_heatmap_payload(
            get_default_sites()[0],
            datetime(2024, 7, 15, tzinfo=UTC),
            aoi_half_size_m=half_size,
        )
