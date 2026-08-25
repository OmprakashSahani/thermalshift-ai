"""Bounded live Scenario Lab API tests; all execution is local and offline."""

import json
from pathlib import Path

import httpx
import pytest

from thermalshift.web.app import create_app

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"
VALID = {
    "window_id": "summer-midday-v1", "gpu_demand": 16, "duration_hours": 2,
    "release_offset_hours": 0, "deadline_offset_hours": 4,
    "eligible_site_ids": ["ashburn-va", "phoenix-az", "san-antonio-tx", "atlanta-ga"],
}


async def post(payload: dict[str, object]) -> httpx.Response:
    transport = httpx.ASGITransport(app=create_app(EVIDENCE))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post("/api/scenario", json=payload)


@pytest.mark.parametrize("window_id", ["summer-midday-v1", "winter-overnight-v1"])
async def test_valid_request_runs_all_schedulers(window_id: str) -> None:
    response = await post({**VALID, "window_id": window_id})
    assert response.status_code == 200
    result = response.json()
    assert result["classification"] == "interactive_simulation"
    assert result["official_benchmark_evidence"] is False
    assert [run["scheduler_name"] for run in result["schedulers"]] == [
        "first_available", "capacity_only", "thermalshift"
    ]
    assert all("whatif" in run["scheduled_workload_ids"] for run in result["schedulers"])
    assert all(run["total_workload_count"] == 11 for run in result["schedulers"])
    assert "not the committed hackathon benchmark" in result["statement"]
    assert "not cooling, energy" in result["comparison_boundary"]
    assert all(run["whatif"]["capacity_satisfied"] for run in result["schedulers"])
    assert all(run["whatif"]["deadline_satisfied"] for run in result["schedulers"])
    serialized = json.dumps(result).casefold()
    for forbidden in ("api_key", "activity_id", "cache_key", "map_data", "payload"):
        assert forbidden not in serialized


@pytest.mark.parametrize("change", [
    {"eligible_site_ids": ["unknown"]}, {"eligible_site_ids": []}, {"gpu_demand": 65},
    {"duration_hours": 4}, {"release_offset_hours": 4, "deadline_offset_hours": 3},
    {"duration_hours": 3, "release_offset_hours": 2, "deadline_offset_hours": 4},
    {"eligible_site_ids": ["ashburn-va", "ashburn-va"]}, {"scheduler_settings": {}},
    {"gpu_demand": "16"}, {"duration_hours": "2"},
])
async def test_invalid_requests_are_rejected(change: dict[str, object]) -> None:
    response = await post({**VALID, **change})
    assert response.status_code == 422


async def test_fairness_uses_conservative_existing_comparison() -> None:
    result = (await post(VALID)).json()
    assert all(item["same_scheduled_workload_set"] for item in result["comparisons"])
    assert all(item["direct_thermal_comparison_valid"] for item in result["comparisons"])
    assert all(item["thermal_exposure_reduction_pct"] is not None for item in result["comparisons"])


async def test_dashboard_contains_isolated_accessible_scenario_lab() -> None:
    transport = httpx.ASGITransport(app=create_app(EVIDENCE))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        html = (await client.get("/")).text
    assert "THERMALSHIFT SCENARIO LAB" in html.upper()
    assert "INTERACTIVE SIMULATION — NOT OFFICIAL BENCHMARK EVIDENCE" in html
    assert 'id="scenario-form"' in html
    assert 'type="submit"' in html
