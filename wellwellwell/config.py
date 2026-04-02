from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_int_csv(value: str, expected_parts: int, name: str) -> tuple[int, ...]:
    parts = tuple(int(part.strip()) for part in value.split(","))
    if len(parts) != expected_parts:
        raise ValueError(f"{name} must contain {expected_parts} comma-separated integers")
    return parts


@dataclass(frozen=True)
class CropRect:
    x: int
    y: int
    width: int
    height: int

    @classmethod
    def from_csv(cls, value: str) -> "CropRect":
        x, y, width, height = _parse_int_csv(value, 4, "WELL_CROP")
        if width <= 0 or height <= 0:
            raise ValueError("WELL_CROP width and height must be positive")
        return cls(x=x, y=y, width=width, height=height)


@dataclass(frozen=True)
class AppConfig:
    data_dir: Path
    db_path: Path
    snapshots_dir: Path
    camera_snapshot_url: str | None
    camera_rtsp_url: str | None
    camera_username: str | None
    camera_password: str | None
    ffmpeg_path: str
    ffmpeg_rtsp_transport: str
    ffmpeg_capture_timeout_seconds: int
    ffmpeg_rw_timeout_microseconds: int
    crop: CropRect
    blue_hsv_lower: tuple[int, int, int]
    blue_hsv_upper: tuple[int, int, int]
    expected_marker_x: int | None
    min_contour_area: int
    empty_y: float
    full_y: float
    full_gallons: float
    save_debug_images: bool
    bind_host: str
    bind_port: int
    enable_collector: bool
    collect_interval_minutes: int
    collect_on_startup: bool
    flush_password: str | None

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> AppConfig:
    load_dotenv()
    cwd = Path.cwd()
    default_data_dir = Path("/data") if Path("/.dockerenv").exists() else cwd / "data"
    data_dir = Path(os.getenv("WELL_DATA_DIR", default_data_dir)).expanduser().resolve()
    db_path = Path(os.getenv("WELL_DB_PATH", data_dir / "wellwellwell.sqlite3")).expanduser().resolve()
    snapshots_dir = Path(
        os.getenv("WELL_SNAPSHOTS_DIR", data_dir / "snapshots")
    ).expanduser().resolve()

    crop = CropRect.from_csv(os.getenv("WELL_CROP", "1450,0,250,580"))
    blue_lower = _parse_int_csv(os.getenv("WELL_BLUE_HSV_LOWER", "90,60,40"), 3, "WELL_BLUE_HSV_LOWER")
    blue_upper = _parse_int_csv(os.getenv("WELL_BLUE_HSV_UPPER", "140,255,255"), 3, "WELL_BLUE_HSV_UPPER")

    expected_marker_x_env = os.getenv("WELL_EXPECTED_MARKER_X")
    expected_marker_x = int(expected_marker_x_env) if expected_marker_x_env else None

    return AppConfig(
        data_dir=data_dir,
        db_path=db_path,
        snapshots_dir=snapshots_dir,
        camera_snapshot_url=os.getenv("CAMERA_SNAPSHOT_URL"),
        camera_rtsp_url=os.getenv("CAMERA_RTSP_URL"),
        camera_username=os.getenv("CAMERA_USERNAME"),
        camera_password=os.getenv("CAMERA_PASSWORD"),
        ffmpeg_path=os.getenv("FFMPEG_PATH", "ffmpeg"),
        ffmpeg_rtsp_transport=os.getenv("FFMPEG_RTSP_TRANSPORT", "tcp"),
        ffmpeg_capture_timeout_seconds=int(os.getenv("FFMPEG_CAPTURE_TIMEOUT_SECONDS", "25")),
        ffmpeg_rw_timeout_microseconds=int(os.getenv("FFMPEG_RW_TIMEOUT_MICROSECONDS", "15000000")),
        crop=crop,
        blue_hsv_lower=blue_lower,
        blue_hsv_upper=blue_upper,
        expected_marker_x=expected_marker_x,
        min_contour_area=int(os.getenv("WELL_MIN_CONTOUR_AREA", "80")),
        empty_y=float(os.getenv("WELL_EMPTY_Y", "190")),
        full_y=float(os.getenv("WELL_FULL_Y", "510")),
        full_gallons=float(os.getenv("WELL_FULL_GALLONS", "7500")),
        save_debug_images=_parse_bool(os.getenv("WELL_SAVE_DEBUG_IMAGES"), True),
        bind_host=os.getenv("WELL_BIND_HOST", "0.0.0.0"),
        bind_port=int(os.getenv("WELL_BIND_PORT", "8000")),
        enable_collector=_parse_bool(os.getenv("WELL_ENABLE_COLLECTOR"), False),
        collect_interval_minutes=int(os.getenv("WELL_COLLECT_INTERVAL_MINUTES", "15")),
        collect_on_startup=_parse_bool(os.getenv("WELL_COLLECT_ON_STARTUP"), True),
        flush_password=os.getenv("WELL_FLUSH_PASSWORD") or None,
    )
