"""Offline tests for bounded replay collection safety."""

from datetime import datetime
from pathlib import Path

import pytest

from examples.collect_historical_replay import (
    CONFIRMATION_VALUE,
    DEFAULT_MAX_API_CALLS,
    main,
    parse_args,
)
from tests.test_fortyguard_models import completed_data
from thermalshift.domain.models import Site, TemperatureObservation
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.client import FortyGuardHTTPError, FortyGuardResponseError
from thermalshift.fortyguard.models import HeatmapResult
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload
from thermalshift.fortyguard.poller import (
    FortyGuardActivityFailed,
    FortyGuardPollingTimeout,
)
from thermalshift.fortyguard.service import FortyGuardStatusRequestError
from thermalshift.replay.adapter import load_calibration_status
from thermalshift.replay.collection import execute_replay_collection
from thermalshift.replay.plan import (
    SUMMER_WINDOW,
    WINTER_WINDOW,
    build_calibration_plan,
    build_replay_plan,
)


def sample_result(mean: float | None = None) -> HeatmapResult:
    value = HeatmapResult.model_validate(completed_data()["result"])
    if mean is None:
        return value
    temperature_stats = value.stats_data.temperature_stats.model_copy(
        update={"mean": mean}
    )
    stats_data = value.stats_data.model_copy(
        update={"temperature_stats": temperature_stats}
    )
    return value.model_copy(update={"stats_data": stats_data})


class CachingFakeService:
    """Fake that mirrors cache-first persistence without network or sleeps."""

    def __init__(
        self,
        cache: HeatmapResultCache,
        *,
        fail_on_call: int | None = None,
        failure_message: str = "fake failure",
        failed_activity_id: str | None = None,
        failure_exception: RuntimeError | None = None,
    ) -> None:
        self.cache = cache
        self.fail_on_call = fail_on_call
        self.failure_message = failure_message
        self.failed_activity_id = failed_activity_id
        self.failure_exception = failure_exception
        self.new_calls: list[tuple[str, datetime]] = []

    async def get_historical_temperature(
        self, site: Site, timestamp: datetime
    ) -> TemperatureObservation:
        payload = build_historical_heatmap_payload(site, timestamp)
        cached = self.cache.get(payload)
        if cached is None:
            self.new_calls.append((site.site_id, timestamp))
            if len(self.new_calls) == self.fail_on_call:
                if self.failure_exception is not None:
                    raise self.failure_exception
                if self.failed_activity_id is not None:
                    raise FortyGuardActivityFailed(self.failed_activity_id)
                raise RuntimeError(self.failure_message)
            cached = sample_result()
            self.cache.put(payload, cached)
        return TemperatureObservation(
            site_id=site.site_id,
            timestamp=timestamp,
            temperature_c=cached.stats_data.temperature_stats.mean,
            observation_type="historical",
        )


def cache_plan_entries(cache: HeatmapResultCache, entries, count: int) -> None:
    sites = {site.site_id: site for site in get_default_sites()}
    for entry in entries[:count]:
        payload = build_historical_heatmap_payload(
            sites[entry.site_id], entry.requested_utc
        )
        cache.put(payload, sample_result())


def test_dry_run_defaults_to_summer_and_makes_no_submissions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls = []

    async def runner(window, limit):
        calls.append((window, limit))
        return 0

    assert main([], submit_runner=runner, cache=HeatmapResultCache(tmp_path)) == 0
    output = capsys.readouterr().out
    assert calls == []
    assert "DRY RUN ONLY" in output
    assert "Replay window: summer-midday-v1" in output
    assert output.count("cache_key=") == 24
    positions = [
        output.index(f"{number:02d} site={site_id}")
        for number, site_id in enumerate(
            ("ashburn-va", "phoenix-az", "san-antonio-tx", "atlanta-ga"),
            start=1,
        )
    ]
    assert positions == sorted(positions)


def test_winter_dry_run_selection(tmp_path: Path, capsys) -> None:
    assert main(
        ["--window", "winter-overnight-v1"],
        cache=HeatmapResultCache(tmp_path),
    ) == 0
    output = capsys.readouterr().out
    assert "Replay window: winter-overnight-v1" in output
    assert "2024-01-15T06:00:00+00:00" in output
    assert output.count("cache_key=") == 24


@pytest.mark.parametrize("confirmation", [None, "WRONG"])
def test_submit_requires_exact_confirmation_without_calling_runner(
    confirmation: str | None, capsys
) -> None:
    calls = []

    async def runner(window, limit):
        calls.append((window, limit))
        return 0

    argv = ["--submit"]
    if confirmation:
        argv.extend(("--confirm", confirmation))
    assert main(argv, submit_runner=runner) == 2
    assert calls == []
    assert CONFIRMATION_VALUE in capsys.readouterr().out


@pytest.mark.parametrize("value", ("0", "-1", "invalid"))
def test_invalid_api_call_limit_is_rejected(value: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(("--max-api-calls", value))


def test_confirmed_cli_passes_only_window_and_conservative_limit() -> None:
    calls = []

    async def runner(window, limit):
        calls.append((window, limit))
        return 0

    assert main(
        (
            "--submit",
            "--confirm",
            CONFIRMATION_VALUE,
            "--max-api-calls",
            "4",
        ),
        submit_runner=runner,
    ) == 0
    assert calls == [(SUMMER_WINDOW, DEFAULT_MAX_API_CALLS)]


def test_submit_requires_explicit_api_call_limit(capsys) -> None:
    calls = []

    async def runner(window, limit):
        calls.append((window, limit))
        return 0

    assert main(("--submit", "--confirm", CONFIRMATION_VALUE), submit_runner=runner) == 2
    assert calls == []
    assert "explicit positive --max-api-calls" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_all_cached_uses_zero_budget_and_reports_complete(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    entries = build_replay_plan(SUMMER_WINDOW, cache).entries
    cache_plan_entries(cache, entries, 24)
    service = CachingFakeService(cache)
    output: list[str] = []
    summary = await execute_replay_collection(
        SUMMER_WINDOW, service, cache, max_api_calls=1, output=output.append
    )
    assert summary.cache_hits == 24
    assert summary.api_calls_made == 0
    assert summary.remaining_uncached == 0
    assert service.new_calls == []
    assert "Replay dataset status: complete" in output


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", (1, 4))
async def test_new_submissions_are_bounded_and_skips_are_counted(
    tmp_path: Path, limit: int
) -> None:
    cache = HeatmapResultCache(tmp_path)
    service = CachingFakeService(cache)
    summary = await execute_replay_collection(
        SUMMER_WINDOW, service, cache, max_api_calls=limit, output=lambda _: None
    )
    assert summary.api_calls_made == limit
    assert summary.collected_successfully == limit
    assert summary.skipped == 24 - limit
    assert summary.remaining_uncached == 24 - limit


@pytest.mark.asyncio
async def test_h0_cache_hits_do_not_consume_budget_and_h1_is_first_new_batch(
    tmp_path: Path,
) -> None:
    cache = HeatmapResultCache(tmp_path)
    entries = build_replay_plan(SUMMER_WINDOW, cache).entries
    cache_plan_entries(cache, entries, 4)
    service = CachingFakeService(cache)
    summary = await execute_replay_collection(
        SUMMER_WINDOW, service, cache, max_api_calls=4, output=lambda _: None
    )
    assert summary.cache_hits == 4
    assert summary.api_calls_made == 4
    assert service.new_calls == [
        (entry.site_id, entry.requested_utc) for entry in entries[4:8]
    ]
    assert {site_id for site_id, _ in service.new_calls} == {
        "ashburn-va",
        "phoenix-az",
        "san-antonio-tx",
        "atlanta-ga",
    }


@pytest.mark.asyncio
async def test_success_persists_and_is_not_resubmitted(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    first_service = CachingFakeService(cache)
    first = await execute_replay_collection(
        WINTER_WINDOW, first_service, cache, max_api_calls=1, output=lambda _: None
    )
    first_call = first_service.new_calls[0]
    second_service = CachingFakeService(cache)
    second = await execute_replay_collection(
        WINTER_WINDOW, second_service, cache, max_api_calls=1, output=lambda _: None
    )
    assert first.collected_successfully == 1
    assert second.cache_hits == 1
    assert first_call not in second_service.new_calls


@pytest.mark.asyncio
async def test_order_is_deterministic_across_fresh_runs(tmp_path: Path) -> None:
    calls = []
    for directory in (tmp_path / "one", tmp_path / "two"):
        cache = HeatmapResultCache(directory)
        service = CachingFakeService(cache)
        await execute_replay_collection(
            SUMMER_WINDOW, service, cache, max_api_calls=4, output=lambda _: None
        )
        calls.append(service.new_calls)
    assert calls[0] == calls[1]


@pytest.mark.asyncio
async def test_failure_stops_new_calls_preserves_success_and_hides_secret(
    tmp_path: Path,
) -> None:
    secret = "fake-secret-must-not-appear"
    cache = HeatmapResultCache(tmp_path)
    service = CachingFakeService(cache, fail_on_call=2, failure_message=secret)
    output: list[str] = []
    summary = await execute_replay_collection(
        SUMMER_WINDOW, service, cache, max_api_calls=4, output=output.append
    )
    entries = build_replay_plan(SUMMER_WINDOW, cache).entries
    sites = {site.site_id: site for site in get_default_sites()}
    first_payload = build_historical_heatmap_payload(
        sites[entries[0].site_id], entries[0].requested_utc
    )
    failed_payload = build_historical_heatmap_payload(
        sites[entries[1].site_id], entries[1].requested_utc
    )
    assert summary.api_calls_made == 2
    assert summary.collected_successfully == 1
    assert summary.failed == 1
    assert summary.skipped == 22
    assert summary.remaining_uncached == 23
    assert cache.contains(first_payload)
    assert not cache.contains(failed_payload)
    rendered = "\n".join(output)
    assert secret not in rendered
    assert "status=FAILED failure_kind=generic_error" in rendered
    assert "activity_id=" not in rendered
    assert "new submissions stopped after failure" in rendered


@pytest.mark.asyncio
async def test_failed_activity_exposes_safe_id_and_stops_later_new_calls(
    tmp_path: Path,
) -> None:
    activity_id = "activity-safe-456"
    cache = HeatmapResultCache(tmp_path)
    service = CachingFakeService(
        cache,
        fail_on_call=2,
        failure_message="api-secret-must-not-appear",
        failed_activity_id=activity_id,
    )
    output: list[str] = []
    summary = await execute_replay_collection(
        SUMMER_WINDOW, service, cache, max_api_calls=4, output=output.append
    )

    rendered = "\n".join(output)
    assert summary.failed == 1
    assert summary.collected_successfully == 1
    assert summary.api_calls_made == 2
    assert len(service.new_calls) == 2
    assert (
        "status=FAILED failure_kind=terminal_activity_failed "
        f"activity_id={activity_id}"
    ) in rendered
    assert "api-secret-must-not-appear" not in rendered
    assert "new submissions stopped after failure" in rendered


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (
            FortyGuardPollingTimeout("activity-timeout"),
            "failure_kind=polling_timeout activity_id=activity-timeout",
        ),
        (
            FortyGuardStatusRequestError(
                "activity-http", "http_error", status_code=429
            ),
            "failure_kind=http_error activity_id=activity-http http_status=429",
        ),
        (
            FortyGuardStatusRequestError("activity-response", "response_error"),
            "failure_kind=response_error activity_id=activity-response",
        ),
        (
            FortyGuardHTTPError(500),
            "failure_kind=http_error http_status=500",
        ),
        (
            FortyGuardResponseError("fake-secret-must-not-appear"),
            "failure_kind=response_error",
        ),
    ),
)
async def test_safe_structured_failure_categories(
    tmp_path: Path, error: RuntimeError, expected: str
) -> None:
    cache = HeatmapResultCache(tmp_path)
    service = CachingFakeService(
        cache, fail_on_call=1, failure_exception=error
    )
    output: list[str] = []

    summary = await execute_replay_collection(
        SUMMER_WINDOW, service, cache, max_api_calls=4, output=output.append
    )

    rendered = "\n".join(output)
    assert summary.failed == 1
    assert summary.api_calls_made == 1
    assert len(service.new_calls) == 1
    assert f"status=FAILED {expected}" in rendered
    assert "fake-secret-must-not-appear" not in rendered


@pytest.mark.asyncio
async def test_calibration_readiness_display_does_not_collect_calibration(
    tmp_path: Path,
) -> None:
    cache = HeatmapResultCache(tmp_path)
    calibration_entries = build_calibration_plan(cache)
    cache_plan_entries(cache, calibration_entries, 27)
    before = load_calibration_status(cache).available_count
    output: list[str] = []
    await execute_replay_collection(
        SUMMER_WINDOW,
        CachingFakeService(cache),
        cache,
        max_api_calls=1,
        output=output.append,
    )
    assert before == load_calibration_status(cache).available_count == 27
    assert "Calibration readiness: 27/28" in output

    ready_cache = HeatmapResultCache(tmp_path / "ready")
    ready_entries = build_calibration_plan(ready_cache)
    sites = {site.site_id: site for site in get_default_sites()}
    for index, entry in enumerate(ready_entries):
        payload = build_historical_heatmap_payload(
            sites[entry.site_id], entry.requested_utc
        )
        ready_cache.put(payload, sample_result(float(index)))
    ready_output: list[str] = []
    await execute_replay_collection(
        SUMMER_WINDOW,
        CachingFakeService(ready_cache),
        ready_cache,
        max_api_calls=1,
        output=ready_output.append,
    )
    assert "Calibration readiness: 28/28 — official replay calibration ready" in ready_output
