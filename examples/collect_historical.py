"""Print the initial offline FortyGuard historical collection plan."""

from dataclasses import dataclass
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache, cache_key_for_payload
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload


@dataclass(frozen=True, slots=True)
class CollectionPlanEntry:
    """One deterministic candidate historical request."""

    site_id: str
    requested_utc: datetime
    site_local_time: datetime
    cache_key: str
    cache_hit: bool


def get_calibration_instants() -> tuple[datetime, ...]:
    """Return seven seasonally and diurnally varied UTC instants in 2024."""
    return (
        datetime(2024, 1, 15, 6, tzinfo=UTC),
        datetime(2024, 3, 20, 15, tzinfo=UTC),
        datetime(2024, 6, 1, 21, tzinfo=UTC),
        datetime(2024, 7, 15, 18, tzinfo=UTC),
        datetime(2024, 8, 31, 3, tzinfo=UTC),
        datetime(2024, 10, 15, 12, tzinfo=UTC),
        datetime(2024, 12, 15, 23, tzinfo=UTC),
    )


def build_collection_plan(
    cache: HeatmapResultCache | None = None,
) -> tuple[CollectionPlanEntry, ...]:
    """Build the offline four-site by seven-instant collection plan."""
    result_cache = cache or HeatmapResultCache()
    entries: list[CollectionPlanEntry] = []
    for site in get_default_sites():
        for timestamp in get_calibration_instants():
            payload = build_historical_heatmap_payload(site, timestamp)
            entries.append(
                CollectionPlanEntry(
                    site_id=site.site_id,
                    requested_utc=timestamp,
                    site_local_time=timestamp.astimezone(ZoneInfo(site.timezone)),
                    cache_key=cache_key_for_payload(payload),
                    cache_hit=result_cache.contains(payload),
                )
            )
    return tuple(entries)


def main() -> int:
    """Print the dry-run-only initial calibration sample plan."""
    entries = build_collection_plan()
    print("DRY RUN ONLY: no FortyGuard API requests will be made.")
    print("Initial calibration sample (not a complete climatic baseline):")
    for request_number, entry in enumerate(entries, start=1):
        print(
            f"{request_number:02d} site={entry.site_id} "
            f"utc={entry.requested_utc.isoformat()} "
            f"local={entry.site_local_time.isoformat()} cache_key={entry.cache_key}"
        )
    print(f"Total planned requests: {len(entries)}")
    print(f"Existing cache hits: {sum(entry.cache_hit for entry in entries)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
