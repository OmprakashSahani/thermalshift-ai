from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from thermalshift.replay.plan import (
    PREDECLARED_WINDOWS,
    SUMMER_WINDOW,
    WINTER_WINDOW,
    build_replay_plan,
)


class EmptyCache:
    def contains(self, _payload):
        return False


class FirstHitCache:
    def __init__(self):
        self.calls = 0

    def contains(self, _payload):
        self.calls += 1
        return self.calls == 1


def test_exactly_two_predeclared_six_hour_windows() -> None:
    assert PREDECLARED_WINDOWS == (SUMMER_WINDOW, WINTER_WINDOW)
    assert SUMMER_WINDOW.start_utc == datetime(2024, 7, 15, 18, tzinfo=UTC)
    assert WINTER_WINDOW.start_utc == datetime(2024, 1, 15, 6, tzinfo=UTC)
    for window in PREDECLARED_WINDOWS:
        assert len(window.instants) == 6
        assert window.instants == tuple(
            window.start_utc + timedelta(hours=offset) for offset in range(6)
        )


def test_plan_is_hour_major_with_four_sites_per_hour() -> None:
    plan = build_replay_plan(SUMMER_WINDOW, EmptyCache())  # type: ignore[arg-type]
    expected_sites = (
        "ashburn-va",
        "phoenix-az",
        "san-antonio-tx",
        "atlanta-ga",
    )
    assert len(plan.entries) == 24
    assert plan.cache_hit_count == 0
    assert plan.missing_count == 24
    for hour in range(6):
        entries = plan.entries[hour * 4 : hour * 4 + 4]
        assert tuple(entry.site_id for entry in entries) == expected_sites
        assert {entry.requested_utc for entry in entries} == {SUMMER_WINDOW.instants[hour]}
    assert tuple(entry.request_number for entry in plan.entries) == tuple(range(1, 25))


def test_cache_hits_and_site_local_conversion_are_auditable() -> None:
    plan = build_replay_plan(SUMMER_WINDOW, FirstHitCache())  # type: ignore[arg-type]
    first = plan.entries[0]
    assert first.cache_hit
    assert plan.cache_hit_count == 1
    assert first.site_local_time == datetime(
        2024, 7, 15, 14, tzinfo=ZoneInfo("America/New_York")
    )
    assert len(first.cache_key) == 64
