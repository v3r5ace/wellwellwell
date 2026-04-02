from __future__ import annotations

from pathlib import Path
import secrets

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import AppConfig, load_config
from .db import fetch_latest_reading, fetch_reading_by_id, fetch_recent_readings, fetch_recent_summary, initialize_database
from .service import collect_once, compute_gallons_remaining, delete_single_reading, flush_history, serialize_reading


class FlushRequest(BaseModel):
    password: str


def create_app(config: AppConfig | None = None) -> FastAPI:
    active_config = config or load_config()
    active_config.ensure_dirs()
    initialize_database(active_config.db_path)

    package_dir = Path(__file__).resolve().parent
    static_dir = package_dir / "static"

    app = FastAPI(title="WellWellWell", version="0.1.0")
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")
    app.mount("/data", StaticFiles(directory=active_config.data_dir), name="data")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/status")
    async def status() -> dict[str, object]:
        latest = fetch_latest_reading(active_config.db_path)
        summary = fetch_recent_summary(active_config.db_path, hours=24)
        if active_config.camera_snapshot_url:
            mode = "snapshot"
        elif active_config.camera_rtsp_url:
            mode = "rtsp"
        else:
            mode = "unconfigured"

        return {
            "camera": {
                "mode": mode,
                "rtsp_transport": active_config.ffmpeg_rtsp_transport,
                "ffmpeg_capture_timeout_seconds": active_config.ffmpeg_capture_timeout_seconds,
                "crop": {
                    "x": active_config.crop.x,
                    "y": active_config.crop.y,
                    "width": active_config.crop.width,
                    "height": active_config.crop.height,
                },
                "calibration": {
                    "empty_y": active_config.empty_y,
                    "full_y": active_config.full_y,
                },
                "full_gallons": active_config.full_gallons,
            },
            "collector": {
                "enabled": active_config.enable_collector,
                "interval_minutes": active_config.collect_interval_minutes,
                "collect_on_startup": active_config.collect_on_startup,
            },
            "admin": {
                "flush_enabled": bool(active_config.flush_password),
            },
            "latest": serialize_reading(latest, active_config),
            "summary": {
                **summary,
                "avg_gallons_remaining": compute_gallons_remaining(
                    summary["avg_percent_full"],
                    active_config.full_gallons,
                ),
            },
        }

    @app.get("/api/readings")
    async def readings(limit: int = Query(default=96, ge=1, le=1000)) -> dict[str, object]:
        records = fetch_recent_readings(active_config.db_path, limit=limit)
        return {
            "items": [serialize_reading(record, active_config) for record in records],
        }

    @app.get("/api/readings/{reading_id}")
    async def get_reading(reading_id: int) -> dict[str, object]:
        record = fetch_reading_by_id(active_config.db_path, reading_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Reading not found")
        return {"reading": serialize_reading(record, active_config)}

    @app.delete("/api/readings/{reading_id}")
    async def delete_reading(reading_id: int, request: FlushRequest) -> dict[str, object]:
        if not active_config.flush_password:
            raise HTTPException(status_code=403, detail="Flush password is not configured")
        if not secrets.compare_digest(request.password, active_config.flush_password):
            raise HTTPException(status_code=403, detail="Invalid flush password")

        try:
            result = delete_single_reading(active_config, reading_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return {"status": "ok", **result}

    @app.post("/api/collect")
    async def collect(sample_image: str | None = None) -> dict[str, object]:
        try:
            reading = collect_once(active_config, Path(sample_image).expanduser().resolve() if sample_image else None)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - useful for operational debugging
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {"reading": serialize_reading(reading, active_config)}

    @app.post("/api/admin/flush")
    async def admin_flush(request: FlushRequest) -> dict[str, object]:
        if not active_config.flush_password:
            raise HTTPException(status_code=403, detail="Flush password is not configured")

        if not secrets.compare_digest(request.password, active_config.flush_password):
            raise HTTPException(status_code=403, detail="Invalid flush password")

        result = flush_history(active_config)
        return {
            "status": "ok",
            **result,
        }

    return app


app = create_app()
