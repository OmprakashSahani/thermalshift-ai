"""Offline tests for one-shot recovery of existing calibration activities."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest

from examples.recover_calibration_activity import (
    CONFIRMATION_VALUE,
    main,
    recover_calibration_activity,
    resolve_calibration_target,
)
from tests.test_fortyguard_models import completed_data, degenerate_null_data
from thermalshift.fortyguard.cache import HeatmapResultCache
from thermalshift.fortyguard.client import FortyGuardClient
from thermalshift.fortyguard.models import HeatmapResult
from thermalshift.fortyguard.payloads import build_historical_heatmap_payload

CANONICAL_TIME = datetime(2024, 12, 15, 23, tzinfo=UTC)


def response(data: dict[str, object]) -> httpx.Response:
    return httpx.Response(200, json={"error": False, "data": data})


def test_invalid_confirmation_and_noncanonical_target_make_zero_requests(capsys) -> None:
    calls: list[str] = []

    async def runner(activity_id, target):
        calls.append(activity_id)
        return 0

    common = [
        "--activity-id",
        "activity-existing",
        "--site-id",
        "atlanta-ga",
        "--requested-utc",
        "2024-12-15T23:00:00Z",
    ]
    assert main([*common, "--confirm", "WRONG"], recovery_runner=runner) == 2
    assert main(
        [
            "--activity-id",
            "activity-existing",
            "--site-id",
            "atlanta-ga",
            "--requested-utc",
            "2024-12-16T23:00:00Z",
            "--confirm",
            CONFIRMATION_VALUE,
        ],
        recovery_runner=runner,
    ) == 2
    assert calls == []
    assert "No API requests were made" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_valid_null_recovery_is_one_get_zero_post_then_cache_hit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    methods: list[str] = []
    data = degenerate_null_data()
    data["activity_id"] = "activity-existing"
    data["result"]["map_data"] = {"secret": "map-secret"}  # type: ignore[index]

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return response(data)

    async def forbidden_sleep(delay: float) -> None:
        raise AssertionError(f"recovery must not sleep: {delay}")

    monkeypatch.setattr(asyncio, "sleep", forbidden_sleep)

    cache = HeatmapResultCache(tmp_path)
    target = resolve_calibration_target("atlanta-ga", CANONICAL_TIME)
    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key", transport=httpx.MockTransport(handler)
    ) as client:
        assert await recover_calibration_activity(
            client,
            cache,
            activity_id="activity-existing",
            target=target,
            output=output.append,
        ) == 0
        assert await recover_calibration_activity(
            client,
            cache,
            activity_id="activity-existing",
            target=target,
            output=output.append,
        ) == 0

    assert methods == ["GET"]
    cached = cache.get(build_historical_heatmap_payload(target.site, CANONICAL_TIME))
    assert cached is not None
    assert cached.stats_data.normal_temperature_distribution.y_axis == [None] * 3
    rendered = "\n".join(output)
    assert "recovery_status=CACHED" in rendered
    assert "recovery_status=CACHE HIT" in rendered
    assert "request_type=GET_STATUS_ONLY" in rendered
    assert "fake-api-key" not in rendered
    assert "map-secret" not in rendered


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["Processing", "Failed"])
async def test_noncompleted_status_is_not_cached(tmp_path: Path, status: str) -> None:
    target = resolve_calibration_target("atlanta-ga", CANONICAL_TIME)
    cache = HeatmapResultCache(tmp_path)
    data = {"activity_id": "activity-existing", "status": status}
    async with FortyGuardClient(
        "fake-api-key", transport=httpx.MockTransport(lambda request: response(data))
    ) as client:
        assert await recover_calibration_activity(
            client, cache, activity_id="activity-existing", target=target
        ) == 1
    assert not cache.contains(build_historical_heatmap_payload(target.site, CANONICAL_TIME))


@pytest.mark.asyncio
async def test_activity_mismatch_is_not_cached(tmp_path: Path) -> None:
    target = resolve_calibration_target("atlanta-ga", CANONICAL_TIME)
    cache = HeatmapResultCache(tmp_path)
    data = completed_data()
    async with FortyGuardClient(
        "fake-api-key", transport=httpx.MockTransport(lambda request: response(data))
    ) as client:
        assert await recover_calibration_activity(
            client, cache, activity_id="different-id", target=target
        ) == 1
    assert not cache.contains(build_historical_heatmap_payload(target.site, CANONICAL_TIME))


@pytest.mark.asyncio
async def test_invalid_completed_result_is_safe_and_not_cached(tmp_path: Path) -> None:
    secret = "raw-secret-must-not-appear"
    data = degenerate_null_data()
    data["activity_id"] = "activity-existing"
    stats = data["result"]["stats_data"]  # type: ignore[index]
    stats["normal_temperature_distribution"]["y_axis"] = [None, secret, None]  # type: ignore[index]
    target = resolve_calibration_target("atlanta-ga", CANONICAL_TIME)
    cache = HeatmapResultCache(tmp_path)
    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key", transport=httpx.MockTransport(lambda request: response(data))
    ) as client:
        assert await recover_calibration_activity(
            client,
            cache,
            activity_id="activity-existing",
            target=target,
            output=output.append,
        ) == 1
    assert not cache.contains(build_historical_heatmap_payload(target.site, CANONICAL_TIME))
    assert secret not in "\n".join(output)


@pytest.mark.asyncio
async def test_completed_without_result_is_not_cached(tmp_path: Path) -> None:
    data = {"activity_id": "activity-existing", "status": "Completed"}
    target = resolve_calibration_target("atlanta-ga", CANONICAL_TIME)
    cache = HeatmapResultCache(tmp_path)
    async with FortyGuardClient(
        "fake-api-key", transport=httpx.MockTransport(lambda request: response(data))
    ) as client:
        assert await recover_calibration_activity(
            client, cache, activity_id="activity-existing", target=target
        ) == 1
    assert not cache.contains(build_historical_heatmap_payload(target.site, CANONICAL_TIME))


@pytest.mark.asyncio
async def test_existing_numeric_cache_hit_makes_zero_requests(tmp_path: Path) -> None:
    class NoRequestClient:
        async def get_status(self, activity_id: str):
            raise AssertionError("cache hit must not GET")

    target = resolve_calibration_target("atlanta-ga", CANONICAL_TIME)
    cache = HeatmapResultCache(tmp_path)
    payload = build_historical_heatmap_payload(target.site, CANONICAL_TIME)
    cache.put(payload, HeatmapResult.model_validate(completed_data()["result"]))

    assert await recover_calibration_activity(
        NoRequestClient(), cache, activity_id="activity-existing", target=target
    ) == 0
