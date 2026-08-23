"""Deterministic FortyGuard heatmap request construction."""

import math
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from thermalshift.domain.models import Site

METERS_PER_LATITUDE_DEGREE = 111_320.0
VALID_GRANULARITIES = frozenset({60, 80, 100})


class FortyGuardPayloadError(ValueError):
    """Raised when a heatmap payload cannot be built safely."""


def build_historical_heatmap_payload(
    site: Site,
    timestamp: datetime,
    *,
    granularity: int = 100,
    aoi_half_size_m: float = 200.0,
) -> dict[str, Any]:
    """Build a single-hour historical TCM request around a modeled site.

    The aware instant is converted to the site's IANA timezone because the
    FortyGuard request shape contains local date/time strings but no timezone.
    """
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise FortyGuardPayloadError("timestamp must be timezone-aware")
    if granularity not in VALID_GRANULARITIES:
        raise FortyGuardPayloadError("granularity must be one of 60, 80, or 100")
    if not math.isfinite(aoi_half_size_m) or aoi_half_size_m <= 0:
        raise FortyGuardPayloadError("AOI half-size must be a positive finite number")

    latitude_delta = aoi_half_size_m / METERS_PER_LATITUDE_DEGREE
    longitude_scale = METERS_PER_LATITUDE_DEGREE * math.cos(math.radians(site.latitude))
    if longitude_scale <= 0:
        raise FortyGuardPayloadError("cannot construct a meter-scale AOI at this latitude")
    longitude_delta = aoi_half_size_m / longitude_scale

    south = site.latitude - latitude_delta
    north = site.latitude + latitude_delta
    west = site.longitude - longitude_delta
    east = site.longitude + longitude_delta
    if south < -90 or north > 90 or west < -180 or east > 180:
        raise FortyGuardPayloadError("AOI coordinates would fall outside valid longitude/latitude")

    local_time = timestamp.astimezone(ZoneInfo(site.timezone))
    ring = [
        [west, south],
        [east, south],
        [east, north],
        [west, north],
        [west, south],
    ]
    return {
        "polygon_aoi": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {"type": "Polygon", "coordinates": [ring]},
                }
            ],
        },
        "date_time": {
            "start_date": local_time.strftime("%Y-%m-%d"),
            "start_time": local_time.strftime("%H:%M"),
            "filter_type": 1,
        },
        "granularity": granularity,
        "analytic_type": "tcm",
    }
