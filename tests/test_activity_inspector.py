"""Offline tests for the one-shot existing-activity inspector."""

import json

import httpx
import pytest

from examples.check_fortyguard_activity import (
    CONFIRMATION_VALUE,
    inspect_activity,
    inspect_activity_shape,
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
    shape_runner_calls: list[str] = []

    async def runner(activity_id: str) -> int:
        runner_calls.append(activity_id)
        return 0

    async def shape_runner(activity_id: str) -> int:
        shape_runner_calls.append(activity_id)
        return 0

    result = main(
        ("--activity-id", "activity-test", "--confirm", "WRONG", "--shape"),
        inspection_runner=runner,
        shape_inspection_runner=shape_runner,
    )

    assert result == 2
    assert runner_calls == []
    assert shape_runner_calls == []
    assert CONFIRMATION_VALUE in capsys.readouterr().out


def test_shape_flag_routes_only_to_shape_runner() -> None:
    normal_calls: list[str] = []
    shape_calls: list[str] = []

    async def normal_runner(activity_id: str) -> int:
        normal_calls.append(activity_id)
        return 0

    async def shape_runner(activity_id: str) -> int:
        shape_calls.append(activity_id)
        return 0

    result = main(
        (
            "--activity-id",
            "activity-test",
            "--confirm",
            CONFIRMATION_VALUE,
            "--shape",
        ),
        inspection_runner=normal_runner,
        shape_inspection_runner=shape_runner,
    )

    assert result == 0
    assert normal_calls == []
    assert shape_calls == ["activity-test"]


def shape_payload(y_axis, *, x_axis=None) -> dict:
    data = completed_data()
    data["activity_id"] = "activity-test"
    distribution = data["result"]["stats_data"]["normal_temperature_distribution"]
    distribution["x_axis"] = [1.0, 2.0] if x_axis is None else x_axis
    distribution["y_axis"] = y_axis
    data["result"]["map_data"] = {"secret": "map-data-must-not-appear"}
    return {"error": False, "data": data}


@pytest.mark.asyncio
async def test_shape_mode_is_one_get_with_numeric_axes_and_safe_stats() -> None:
    methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        return response(shape_payload([3.0, 4.0]))

    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key", transport=httpx.MockTransport(handler)
    ) as client:
        assert await inspect_activity_shape(
            client, "activity-test", output=output.append
        ) == 0

    rendered = "\n".join(output)
    assert methods == ["GET"]
    assert "request_type=GET_STATUS_SHAPE_ONLY" in rendered
    assert "normal_x_axis_length=2" in rendered
    assert "normal_y_axis_length=2" in rendered
    assert "normal_y_axis_types=number:2,null:0,string:0,boolean:0" in rendered
    assert "temperature_mean_c=" in rendered
    assert "map-data-must-not-appear" not in rendered
    assert "fake-api-key" not in rendered


@pytest.mark.asyncio
async def test_shape_mode_counts_100_nulls_without_values() -> None:
    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key",
        transport=httpx.MockTransport(
            lambda request: response(shape_payload([None] * 100))
        ),
    ) as client:
        await inspect_activity_shape(client, "activity-test", output=output.append)

    rendered = "\n".join(output)
    assert "normal_y_axis_length=100" in rendered
    assert "normal_y_axis_types=number:0,null:100,string:0,boolean:0" in rendered


@pytest.mark.asyncio
async def test_shape_mode_classifies_mixed_types_bool_and_nonfinite_numbers() -> None:
    secret = "distribution-secret-must-not-appear"
    values = [1, None, secret, True, {"hidden": secret}, [secret], float("nan"), float("inf")]
    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=json.dumps(shape_payload(values)).encode(),
                headers={"content-type": "application/json"},
            )
        ),
    ) as client:
        await inspect_activity_shape(client, "activity-test", output=output.append)

    rendered = "\n".join(output)
    assert "normal_y_axis_length=8" in rendered
    assert (
        "normal_y_axis_types=number:3,null:1,string:1,boolean:1,"
        "object:1,array:1,other:0"
    ) in rendered
    assert "normal_y_axis_non_finite_numbers=2" in rendered
    assert secret not in rendered


@pytest.mark.asyncio
async def test_shape_mode_handles_missing_result_and_distribution() -> None:
    missing_result = {
        "error": False,
        "data": {"activity_id": "activity-test", "status": "Processing"},
    }
    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key",
        transport=httpx.MockTransport(lambda request: response(missing_result)),
    ) as client:
        await inspect_activity_shape(client, "activity-test", output=output.append)
    rendered = "\n".join(output)
    assert "result_present=false" in rendered
    assert "normal_distribution_present=false" in rendered
    assert "normal_y_axis_length=unavailable" in rendered

    payload = shape_payload([1])
    del payload["data"]["result"]["stats_data"]["normal_temperature_distribution"]
    second_output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key",
        transport=httpx.MockTransport(lambda request: response(payload)),
    ) as client:
        await inspect_activity_shape(client, "activity-test", output=second_output.append)
    assert "normal_distribution_present=false" in "\n".join(second_output)


@pytest.mark.asyncio
async def test_shape_mode_suppresses_invalid_temperature_stat_values() -> None:
    secret = "temperature-secret-must-not-appear"
    payload = shape_payload([1])
    temperature = payload["data"]["result"]["stats_data"]["temperature_stats"]
    temperature.update(
        {
            "minimum": None,
            "maximum": secret,
            "mean": {"secret": secret},
            "standard_deviation": True,
        }
    )
    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key",
        transport=httpx.MockTransport(lambda request: response(payload)),
    ) as client:
        await inspect_activity_shape(client, "activity-test", output=output.append)

    rendered = "\n".join(output)
    assert "temperature_min_c=unavailable" in rendered
    assert "temperature_max_c=unavailable" in rendered
    assert "temperature_mean_c=unavailable" in rendered
    assert "temperature_stddev_c=unavailable" in rendered
    assert secret not in rendered


@pytest.mark.asyncio
async def test_shape_mode_error_envelope_remains_safe() -> None:
    secret = "server-secret-must-not-appear"
    output: list[str] = []
    async with FortyGuardClient(
        "fake-api-key",
        transport=httpx.MockTransport(
            lambda request: response({"error": True, "message": secret})
        ),
    ) as client:
        assert await inspect_activity_shape(
            client, "activity-test", output=output.append
        ) == 1

    rendered = "\n".join(output)
    assert rendered.endswith("response_reason=api_error")
    assert secret not in rendered
