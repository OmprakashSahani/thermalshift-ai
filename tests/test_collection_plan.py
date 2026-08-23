"""Tests for safe bounded historical collection."""

from datetime import datetime
from pathlib import Path

import pytest

from examples.collect_historical import (
    CONFIRMATION_VALUE,
    build_collection_plan,
    execute_collection,
    get_calibration_instants,
    get_submission_order,
    main,
    parse_args,
)
from tests.test_fortyguard_models import completed_data
from thermalshift.domain.models import Site, TemperatureObservation
from thermalshift.domain.sites import get_default_sites
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.models import HeatmapResult
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload


def sample_result() -> HeatmapResult:
    return HeatmapResult.model_validate(completed_data()["result"])


class CachingFakeService:
    """Offline service fake that mirrors successful cache persistence."""

    def __init__(
        self,
        cache: HeatmapResultCache,
        *,
        fail_on_new_call: int | None = None,
        failure_message: str = "fake failure",
    ) -> None:
        self.cache = cache
        self.fail_on_new_call = fail_on_new_call
        self.failure_message = failure_message
        self.new_submission_site_ids: list[str] = []

    async def get_historical_temperature(
        self, site: Site, timestamp: datetime
    ) -> TemperatureObservation:
        payload = build_historical_heatmap_payload(site, timestamp)
        result = self.cache.get(payload)
        if result is None:
            self.new_submission_site_ids.append(site.site_id)
            if len(self.new_submission_site_ids) == self.fail_on_new_call:
                raise RuntimeError(self.failure_message)
            result = sample_result()
            self.cache.put(payload, result)
        return TemperatureObservation(
            site_id=site.site_id,
            timestamp=timestamp,
            temperature_c=result.stats_data.temperature_stats.mean,
            observation_type="historical",
        )


def cache_entries(cache: HeatmapResultCache, count: int) -> None:
    plan = build_collection_plan(cache)
    sites = {site.site_id: site for site in get_default_sites()}
    for entry in plan[:count]:
        payload = build_historical_heatmap_payload(sites[entry.site_id], entry.requested_utc)
        cache.put(payload, sample_result())


def test_default_plan_has_four_sites_times_seven_instants(tmp_path: Path) -> None:
    entries = build_collection_plan(HeatmapResultCache(tmp_path))

    assert len(entries) == 28
    assert len({entry.site_id for entry in entries}) == 4
    assert len({entry.requested_utc for entry in entries}) == 7
    assert all(not entry.cache_hit for entry in entries)


def test_instants_are_unique_2024_utc_values_with_varied_hours() -> None:
    instants = get_calibration_instants()

    assert len(instants) == len(set(instants)) == 7
    assert all(instant.year == 2024 for instant in instants)
    assert all(instant.utcoffset().total_seconds() == 0 for instant in instants)
    assert len({instant.hour for instant in instants}) == 7


def test_default_invocation_stays_dry_run(capsys: pytest.CaptureFixture[str]) -> None:
    runner_calls: list[int] = []

    async def runner(max_api_calls: int) -> int:
        runner_calls.append(max_api_calls)
        return 0

    assert main([], submit_runner=runner) == 0
    assert runner_calls == []
    assert "DRY RUN ONLY" in capsys.readouterr().out


@pytest.mark.parametrize("confirmation", [None, "WRONG_CONFIRMATION"])
def test_submit_without_exact_confirmation_makes_zero_calls(
    confirmation: str | None, capsys: pytest.CaptureFixture[str]
) -> None:
    runner_calls: list[int] = []

    async def runner(max_api_calls: int) -> int:
        runner_calls.append(max_api_calls)
        return 0

    argv = ["--submit"]
    if confirmation is not None:
        argv.extend(["--confirm", confirmation])

    assert main(argv, submit_runner=runner) != 0
    assert runner_calls == []
    assert CONFIRMATION_VALUE in capsys.readouterr().out


@pytest.mark.parametrize("value", ["0", "-1", "not-an-integer"])
def test_invalid_max_api_calls_is_rejected(value: str) -> None:
    with pytest.raises(SystemExit):
        parse_args(["--max-api-calls", value])


@pytest.mark.asyncio
async def test_four_call_preflight_covers_four_distinct_sites(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    service = CachingFakeService(cache)

    summary = await execute_collection(service, cache, max_api_calls=4, output=lambda line: None)

    assert summary.api_calls_made == 4
    assert summary.collected_successfully == 4
    assert service.new_submission_site_ids == [
        "ashburn-va",
        "phoenix-az",
        "san-antonio-tx",
        "atlanta-ga",
    ]


@pytest.mark.asyncio
async def test_cache_hits_do_not_consume_budget(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    cache_entries(cache, 1)
    service = CachingFakeService(cache)

    summary = await execute_collection(service, cache, max_api_calls=4, output=lambda line: None)

    assert summary.cache_hits == 1
    assert summary.api_calls_made == 4
    assert summary.collected_successfully == 4


@pytest.mark.asyncio
async def test_success_is_persisted_and_reused(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    first_service = CachingFakeService(cache)

    first = await execute_collection(
        first_service, cache, max_api_calls=1, output=lambda line: None
    )
    second_service = CachingFakeService(cache)
    second = await execute_collection(
        second_service, cache, max_api_calls=1, output=lambda line: None
    )

    assert first.collected_successfully == 1
    assert second.cache_hits == 1
    assert second.api_calls_made == 1
    assert len(second_service.new_submission_site_ids) == 1


@pytest.mark.asyncio
async def test_failure_stops_additional_new_submissions_and_hides_secret(tmp_path: Path) -> None:
    secret = "must-not-appear"
    cache = HeatmapResultCache(tmp_path)
    service = CachingFakeService(cache, fail_on_new_call=2, failure_message=secret)
    output: list[str] = []

    summary = await execute_collection(service, cache, max_api_calls=4, output=output.append)

    assert summary.api_calls_made == 2
    assert summary.collected_successfully == 1
    assert summary.failed == 1
    assert summary.skipped == 26
    assert summary.remaining_uncached == 27
    assert secret not in "\n".join(output)


@pytest.mark.asyncio
async def test_summary_counts_for_bounded_empty_cache(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    service = CachingFakeService(cache)

    summary = await execute_collection(service, cache, max_api_calls=4, output=lambda line: None)

    assert summary.planned_entries == 28
    assert summary.cache_hits == 0
    assert summary.api_calls_made == 4
    assert summary.collected_successfully == 4
    assert summary.failed == 0
    assert summary.skipped == 24
    assert summary.remaining_uncached == 24


def test_submission_order_is_deterministic(tmp_path: Path) -> None:
    first = get_submission_order(build_collection_plan(HeatmapResultCache(tmp_path / "one")))
    second = get_submission_order(build_collection_plan(HeatmapResultCache(tmp_path / "two")))

    assert [(entry.site_id, entry.requested_utc) for entry in first] == [
        (entry.site_id, entry.requested_utc) for entry in second
    ]


@pytest.mark.asyncio
async def test_all_cached_scenario_makes_zero_new_calls(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    cache_entries(cache, 28)
    service = CachingFakeService(cache)

    summary = await execute_collection(service, cache, max_api_calls=4, output=lambda line: None)

    assert summary.cache_hits == 28
    assert summary.api_calls_made == 0
    assert summary.skipped == 0
    assert summary.remaining_uncached == 0
    assert service.new_submission_site_ids == []


@pytest.mark.asyncio
async def test_partially_cached_plan_submits_only_missing_entries(tmp_path: Path) -> None:
    cache = HeatmapResultCache(tmp_path)
    cache_entries(cache, 26)
    service = CachingFakeService(cache)

    summary = await execute_collection(service, cache, max_api_calls=4, output=lambda line: None)

    assert summary.cache_hits == 26
    assert summary.api_calls_made == 2
    assert summary.collected_successfully == 2
    assert summary.remaining_uncached == 0


def test_confirmed_cli_passes_conservative_budget_to_runner() -> None:
    budgets: list[int] = []

    async def runner(max_api_calls: int) -> int:
        budgets.append(max_api_calls)
        return 0

    result = main(
        ["--submit", "--confirm", CONFIRMATION_VALUE, "--max-api-calls", "4"],
        submit_runner=runner,
    )

    assert result == 0
    assert budgets == [4]
