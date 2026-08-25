"""FastAPI application for the offline ThermalShift judge demo."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, Response

from .evidence import EvidenceLoadError, load_all_evidence, load_window_evidence
from .scenario import ScenarioRequest, run_scenario
from .thermal_grid import ThermalGridArtifactError

PACKAGE_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]
DEFAULT_EVIDENCE_ROOT = REPOSITORY_ROOT / "evidence"
STATIC_ROOT = PACKAGE_ROOT / "static"


def create_app(evidence_root: Path = DEFAULT_EVIDENCE_ROOT) -> FastAPI:
    """Create the offline dashboard application for a selected evidence directory."""
    index_html = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")
    stylesheet = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")
    javascript = (STATIC_ROOT / "app.js").read_text(encoding="utf-8")
    application = FastAPI(
        title="ThermalShift AI Judge Demo",
        description="Committed evidence plus ephemeral live scheduling simulation.",
        version="0.1.0",
    )

    @application.get("/", include_in_schema=False)
    async def dashboard() -> HTMLResponse:
        return HTMLResponse(index_html)

    @application.get("/static/app.css", include_in_schema=False)
    async def app_css() -> Response:
        return Response(stylesheet, media_type="text/css")

    @application.get("/static/app.js", include_in_schema=False)
    async def app_javascript() -> Response:
        return Response(javascript, media_type="text/javascript")

    @application.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "healthy", "mode": "evidence-and-interactive-simulation"}

    @application.get("/api/evidence")
    async def all_evidence() -> dict[str, object]:
        try:
            return load_all_evidence(evidence_root)
        except EvidenceLoadError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @application.get("/api/evidence/{window_id}")
    async def window_evidence(window_id: str) -> dict[str, object]:
        try:
            return load_window_evidence(evidence_root, window_id)
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Unknown evidence window") from error
        except EvidenceLoadError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    @application.post("/api/scenario")
    async def scenario(request: ScenarioRequest) -> dict[str, object]:
        try:
            return run_scenario(request, evidence_root)
        except ThermalGridArtifactError as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    return application


app = create_app()
