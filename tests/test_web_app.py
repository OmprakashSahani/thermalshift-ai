"""Offline route tests for the ThermalShift judge dashboard."""

from pathlib import Path

import httpx

from thermalshift.web.app import create_app

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = REPOSITORY_ROOT / "evidence"


async def get(path: str, evidence_root: Path = EVIDENCE_ROOT) -> httpx.Response:
    transport = httpx.ASGITransport(app=create_app(evidence_root))
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def test_dashboard_returns_local_html() -> None:
    response = await get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "ThermalShift AI" in response.text
    assert "/static/app.css" in response.text
    assert "/static/app.js" in response.text
    assert "FORTYGUARD-BACKED HISTORICAL EVIDENCE" not in response.text


async def test_healthz_is_lightweight_and_healthy() -> None:
    response = await get("/healthz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "mode": "evidence-and-interactive-simulation",
    }


async def test_all_evidence_route_returns_both_windows() -> None:
    response = await get("/api/evidence")

    assert response.status_code == 200
    result = response.json()
    assert result["evidence_type"] == "fortyguard_historical_replay"
    assert result["default_window_id"] == "summer-midday-v1"
    assert len(result["windows"]) == 2


async def test_each_known_window_route_returns_selected_evidence() -> None:
    summer = await get("/api/evidence/summer-midday-v1")
    winter = await get("/api/evidence/winter-overnight-v1")

    assert summer.status_code == 200
    assert summer.json()["window_id"] == "summer-midday-v1"
    assert summer.json()["is_primary"] is True
    assert winter.status_code == 200
    assert winter.json()["window_id"] == "winter-overnight-v1"
    assert winter.json()["zero_floor"]["applies"] is True


async def test_unknown_window_returns_404() -> None:
    response = await get("/api/evidence/not-a-window")

    assert response.status_code == 404
    assert response.json() == {"detail": "Unknown evidence window"}


async def test_missing_committed_evidence_returns_clear_503(tmp_path: Path) -> None:
    response = await get("/api/evidence", tmp_path)

    assert response.status_code == 503
    assert "Committed evidence is missing" in response.json()["detail"]


async def test_static_assets_resolve_without_external_dependencies() -> None:
    css = await get("/static/app.css")
    javascript = await get("/static/app.js")

    assert css.status_code == 200
    assert css.headers["content-type"].startswith("text/css")
    assert javascript.status_code == 200
    assert "fetch(\"/api/evidence\"" in javascript.text
    assert "http://" not in css.text
    assert "https://" not in css.text
    assert "http://" not in javascript.text
    assert "https://" not in javascript.text
    assert 'aria-pressed' in javascript.text
    assert 'scope=\\"col\\"' in javascript.text
    assert 'heading.scope = "row"' in javascript.text
    assert 'byId("scenario-result").hidden = true' in javascript.text
    assert "No synthetic substitute was used" in javascript.text
    assert "prefers-reduced-motion" in css.text
    assert 'fetch("/api/scenario"' in javascript.text
    assert "http://" not in javascript.text


async def test_default_paths_work_after_current_directory_changes(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    dashboard = await get("/")
    evidence = await get("/api/evidence")

    assert dashboard.status_code == 200
    assert evidence.status_code == 200
    assert evidence.json()["default_window_id"] == "summer-midday-v1"
