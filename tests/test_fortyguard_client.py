"""Tests for the asynchronous FortyGuard HTTP client."""

import httpx
import pytest

from tests.test_fortyguard_models import completed_data
from thermalshift.fortyguard.client import (
    FortyGuardClient,
    FortyGuardHTTPError,
    FortyGuardResponseError,
)
from thermalshift.fortyguard.models import ActivityStatus


def response(payload: object, status_code: int = 200) -> httpx.Response:
    return httpx.Response(status_code, json=payload)


@pytest.mark.asyncio
async def test_submit_heatmap_returns_activity_id_and_sends_headers() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["api-key"] == "unit-test-key"
        assert request.headers["content-type"] == "application/json"
        assert request.headers["accept"] == "application/json"
        return response({"error": False, "data": {"activity_id": "activity-123"}})

    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(handler)
    ) as client:
        activity_id = await client.submit_heatmap({"known": "payload"})

    assert activity_id == "activity-123"


@pytest.mark.asyncio
async def test_completed_status_returns_typed_activity_status() -> None:
    transport = httpx.MockTransport(
        lambda request: response({"error": False, "data": completed_data()})
    )
    async with FortyGuardClient("unit-test-key", transport=transport) as client:
        status = await client.get_status("activity-123")

    assert isinstance(status, ActivityStatus)
    assert status.result is not None


@pytest.mark.asyncio
async def test_processing_status_is_valid() -> None:
    payload = {
        "error": False,
        "data": {"activity_id": "activity-123", "status": "Processing"},
    }
    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(lambda request: response(payload))
    ) as client:
        status = await client.get_status("activity-123")

    assert status.status == "Processing"
    assert status.result is None


@pytest.mark.parametrize("status_code", (429, 500))
@pytest.mark.asyncio
async def test_http_error_preserves_numeric_status(status_code: int) -> None:
    transport = httpx.MockTransport(lambda request: response({}, status_code=status_code))
    async with FortyGuardClient("unit-test-key", transport=transport) as client:
        with pytest.raises(FortyGuardHTTPError) as caught:
            await client.get_status("activity-123")

    assert caught.value.status_code == status_code
    assert f"HTTP {status_code}" in str(caught.value)
    assert "unit-test-key" not in str(caught.value)


@pytest.mark.asyncio
async def test_transport_error_has_no_status_or_credentials() -> None:
    key = "unit-test-key"

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(f"transport failed with {key}", request=request)

    async with FortyGuardClient(key, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(FortyGuardHTTPError) as caught:
            await client.submit_heatmap({})

    assert caught.value.status_code is None
    assert key not in str(caught.value)


@pytest.mark.asyncio
async def test_api_error_payload_becomes_response_error_without_exposing_key() -> None:
    key = "unit-test-key"
    payload = {"error": True, "message": f"Invalid credential {key}"}
    async with FortyGuardClient(
        key, transport=httpx.MockTransport(lambda request: response(payload))
    ) as client:
        with pytest.raises(FortyGuardResponseError) as exc_info:
            await client.submit_heatmap({})

    assert exc_info.value.reason_code == "api_error"
    assert key not in str(exc_info.value)
    assert "Invalid credential" not in str(exc_info.value)


@pytest.mark.asyncio
async def test_missing_submission_activity_id_is_rejected() -> None:
    payload = {"error": False, "data": {}}
    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(lambda request: response(payload))
    ) as client:
        with pytest.raises(FortyGuardResponseError) as caught:
            await client.submit_heatmap({})

    assert caught.value.reason_code == "missing_activity_id"
    assert caught.value.validation_paths == (("activity_id",),)


@pytest.mark.asyncio
async def test_malformed_completed_status_is_rejected() -> None:
    payload = {
        "error": False,
        "data": {"activity_id": "activity-123", "status": "Completed", "result": {}},
    }
    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(lambda request: response(payload))
    ) as client:
        with pytest.raises(FortyGuardResponseError) as caught:
            await client.get_status("activity-123")

    assert caught.value.reason_code == "malformed_activity_status"
    assert caught.value.validation_paths
    assert all(
        isinstance(component, str)
        for path in caught.value.validation_paths
        for component in path
    )
    assert "{}" not in str(caught.value.validation_paths)


@pytest.mark.asyncio
async def test_non_json_response_is_rejected() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, text="not JSON", headers={"content-type": "text/plain"})
    )
    async with FortyGuardClient("unit-test-key", transport=transport) as client:
        with pytest.raises(FortyGuardResponseError) as caught:
            await client.get_status("activity-123")

    assert caught.value.reason_code == "non_json_response"


def test_blank_api_key_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be blank"):
        FortyGuardClient("   ")


@pytest.mark.asyncio
async def test_blank_activity_id_is_rejected_without_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        pytest.fail("No HTTP request should be made for a blank activity ID")

    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(ValueError, match="must not be blank"):
            await client.get_status("  ")


@pytest.mark.asyncio
async def test_unexpected_top_level_structure_is_rejected() -> None:
    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(lambda request: response([]))
    ) as client:
        with pytest.raises(FortyGuardResponseError) as caught:
            await client.submit_heatmap({})

    assert caught.value.reason_code == "unexpected_envelope"


@pytest.mark.asyncio
async def test_missing_data_has_structured_reason() -> None:
    payload = {"error": False}
    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(lambda request: response(payload))
    ) as client:
        with pytest.raises(FortyGuardResponseError) as caught:
            await client.get_status("activity-123")

    assert caught.value.reason_code == "missing_data"


@pytest.mark.asyncio
async def test_completed_without_result_has_structured_reason() -> None:
    payload = {
        "error": False,
        "data": {"activity_id": "activity-123", "status": "Completed"},
    }
    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(lambda request: response(payload))
    ) as client:
        with pytest.raises(FortyGuardResponseError) as caught:
            await client.get_status("activity-123")

    assert caught.value.reason_code == "completed_missing_result"
    assert caught.value.validation_paths == (("result",),)


@pytest.mark.asyncio
async def test_failed_status_remains_a_valid_activity_status() -> None:
    payload = {
        "error": False,
        "data": {"activity_id": "activity-123", "status": "Failed"},
    }
    async with FortyGuardClient(
        "unit-test-key", transport=httpx.MockTransport(lambda request: response(payload))
    ) as client:
        status = await client.get_status("activity-123")

    assert status.status == "Failed"
    assert status.result is None
