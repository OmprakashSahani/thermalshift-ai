"""Offline tests for the one-shot existing-activity inspector."""

import httpx
import pytest

from examples.check_fortyguard_activity import (
    CONFIRMATION_VALUE,
    inspect_activity,
    main,
)
from tests.test_fortyguard_models import completed_data
from thermalshift.fortyguard.client import FortyGuardClient


def response(payload: object, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


@pytest.mark.asyncio
async def test_inspector_performs_exactly_one_get_and_zero_posts() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return response(
            {
                "error": False,
                "data": {
                    "activity_id": "activity-test",
                    "status": "Processing",
                },
            }
        )

    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key", transport=httpx.MockTransport(handler)
    ) as client:
        assert await inspect_activity(client, "activity-test", output=output.append) == 0

    assert methods == ["GET"]
    assert "request_type=GET_STATUS_ONLY" in output
    assert "status=Processing" in output
    assert "result_present=false" in output
    assert "fake-api-key" not in "\n".join(output)


@pytest.mark.asyncio
async def test_inspector_prints_safe_completed_aggregate_without_map_data() -> None:
    payload = {"error": False, "data": completed_data()}
    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key",
        transport=httpx.MockTransport(lambda request: response(payload)),
    ) as client:
        assert await inspect_activity(client, "activity-123", output=output.append) == 0

    rendered = "\n".join(output)
    assert "status=Completed" in rendered
    assert "result_present=true" in rendered
    assert "mean_temperature_c=" in rendered
    assert "map_data" not in rendered


@pytest.mark.asyncio
async def test_inspector_suppresses_raw_error_body_and_key() -> None:
    key = "fake-api-key"
    raw_body_secret = "raw-body-must-not-appear"
    payload = {"error": True, "message": raw_body_secret}
    output: list[str] = []
    async with FortyGuardClient(
        key, transport=httpx.MockTransport(lambda request: response(payload))
    ) as client:
        assert await inspect_activity(client, "activity-123", output=output.append) == 1

    rendered = "\n".join(output)
    assert rendered == (
        "status_check=FAILED failure_kind=response_error response_reason=api_error"
    )
    assert key not in rendered
    assert raw_body_secret not in rendered


def test_invalid_confirmation_makes_zero_requests(capsys) -> None:
    runner_calls: list[str] = []

    async def runner(activity_id: str) -> int:
        runner_calls.append(activity_id)
        return 0

    result = main(
        ("--activity-id", "activity-test", "--confirm", "WRONG"),
        inspection_runner=runner,
    )

    assert result == 2
    assert runner_calls == []
    assert CONFIRMATION_VALUE in capsys.readouterr().out
