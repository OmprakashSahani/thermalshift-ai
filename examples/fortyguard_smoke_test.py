"""Safely preview or explicitly submit a small FortyGuard heatmap request."""

import argparse
import asyncio
import json
from collections.abc import Sequence
from typing import Any

from thermalshift.config import get_settings
from thermalshift.fortyguard.client import FortyGuardClient, FortyGuardError
from thermalshift.fortyguard.poller import FortyGuardPollingError
from thermalshift.fortyguard.service import create_heatmap


def build_heatmap_payload() -> dict[str, Any]:
    """Build the known-valid historical Ashburn heatmap request payload."""
    return {
        "polygon_aoi": {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [-77.4895, 39.0417],
                                [-77.4855, 39.0417],
                                [-77.4855, 39.0457],
                                [-77.4895, 39.0457],
                                [-77.4895, 39.0417],
                            ]
                        ],
                    },
                }
            ],
        },
        "date_time": {
            "start_date": "2024-07-15",
            "start_time": "14:00",
            "filter_type": 1,
        },
        "granularity": 100,
        "analytic_type": "tcm",
    }


async def submit_heatmap(payload: dict[str, Any]) -> None:
    """Submit the smoke-test payload and print only safe summary statistics."""
    settings = get_settings()
    api_key = settings.require_fortyguard_api_key()

    async with FortyGuardClient(
        api_key=api_key,
        base_url=settings.fortyguard_base_url,
    ) as client:
        result = await create_heatmap(client, payload)

    stats = result.stats_data.temperature_stats
    print("Activity status: Completed")
    print(f"Minimum temperature: {stats.minimum}")
    print(f"Maximum temperature: {stats.maximum}")
    print(f"Mean temperature: {stats.mean}")
    print(f"Standard deviation: {stats.standard_deviation}")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse smoke-test command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--submit",
        action="store_true",
        help="explicitly submit the request to FortyGuard instead of performing a dry run",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Preview the payload by default or explicitly submit it."""
    args = parse_args(argv)
    payload = build_heatmap_payload()

    if not args.submit:
        print("DRY RUN: no FortyGuard API request will be made.")
        print(json.dumps(payload, indent=2))
        return 0

    try:
        asyncio.run(submit_heatmap(payload))
    except (FortyGuardError, FortyGuardPollingError, RuntimeError, ValueError) as exc:
        print(f"Smoke test failed: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
