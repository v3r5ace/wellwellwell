from __future__ import annotations

import secrets

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from pydantic import BaseModel

from .config import AppConfig, load_config
from .db import fetch_latest_reading, fetch_reading_by_id, fetch_recent_readings, fetch_recent_summary, initialize_database
from .ratelimit import auth_fail_limiter, collect_limiter
from .service import collect_once, compute_gallons_remaining, delete_single_reading, flush_history, serialize_reading

BLOCKED_EXTENSIONS = {".sqlite3", ".db", ".sqlite", ".sql", ".env"}


class FlushRequest(BaseModel):
    password: str


def _check_auth(config: AppConfig, password: str) -> None:
    if not config.flush_password:
        raise HTTPException(status_code=403, detail="Flush password is not configured")

    if not auth_fail_limiter.allow():
        raise HTTPException(status_code=429, detail="Too many failed attempts, try again later")

    if not secrets.compare_digest(password, config.flush_password):
        raise HTTPException(status_code=403, detail="Invalid flush password")

    # Successful auth — give back the slot we just consumed.
    auth_fail_limiter.reset()


def create_app(config: AppConfig | None = None) -> FastAPI:
    active_config = config or load_config()
    active_config.ensure_dirs()
    initialize_database(active_config.db_path)

    package_dir = Path(__file__).resolve().parent
    static_dir = package_dir / "static"

    app = FastAPI(title="WellWellWell", version="0.1.0")
    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")
    app.mount("/data", StaticFiles(directory=active_config.data_dir), name="data")

    @app.middleware("http")
    async def block_sensitive_files(request: Request, call_next) -> Response:
        if request.url.path.startswith("/data/"):
            suffix = Path(request.url.path).suffix.lower()
            if suffix in BLOCKED_EXTENSIONS:
                return Response(status_code=404)
        return await call_next(request)

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

        return {
            "collector": {
                "enabled": active_config.enable_collector,
                "interval_minutes": active_config.collect_interval_minutes,
            },
            "admin": {
                "flush_enabled": bool(active_config.flush_password),
            },
            "collect_remaining": collect_limiter.remaining,
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
    async def readings(
        limit: int = Query(default=1000, ge=1, le=10000),
        since: str | None = Query(default=None),
    ) -> dict[str, object]:
        records = fetch_recent_readings(active_config.db_path, limit=limit, since=since)
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
        _check_auth(active_config, request.password)

        try:
            result = delete_single_reading(active_config, reading_id)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

        return {"status": "ok", **result}

    @app.post("/api/collect")
    async def collect() -> dict[str, object]:
        if not collect_limiter.allow():
            raise HTTPException(
                status_code=429,
                detail="Collection rate limit reached (5 per hour). Resets on next scheduled collection.",
            )

        try:
            reading = collect_once(active_config)
        except Exception as exc:  # pragma: no cover - useful for operational debugging
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {"reading": serialize_reading(reading, active_config)}

    @app.post("/api/admin/flush")
    async def admin_flush(request: FlushRequest) -> dict[str, object]:
        _check_auth(active_config, request.password)

        result = flush_history(active_config)
        return {
            "status": "ok",
            **result,
        }

    return app


app = create_app()
