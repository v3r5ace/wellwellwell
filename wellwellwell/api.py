from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import AppConfig, load_config
from .db import fetch_latest_reading, fetch_recent_readings, fetch_recent_summary, initialize_database
from .service import collect_once, serialize_reading


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
            },
            "collector": {
                "enabled": active_config.enable_collector,
                "interval_minutes": active_config.collect_interval_minutes,
                "collect_on_startup": active_config.collect_on_startup,
            },
            "latest": serialize_reading(latest),
            "summary": summary,
        }

    @app.get("/api/readings")
    async def readings(limit: int = Query(default=96, ge=1, le=1000)) -> dict[str, object]:
        records = fetch_recent_readings(active_config.db_path, limit=limit)
        return {
            "items": [serialize_reading(record) for record in records],
        }

    @app.post("/api/collect")
    async def collect(sample_image: str | None = None) -> dict[str, object]:
        try:
            reading = collect_once(active_config, Path(sample_image).expanduser().resolve() if sample_image else None)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except Exception as exc:  # pragma: no cover - useful for operational debugging
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {"reading": serialize_reading(reading)}

    return app


app = create_app()
