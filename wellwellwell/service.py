from __future__ import annotations

import shutil
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2

from .capture import capture_snapshot, ingest_local_image
from .config import AppConfig
from .db import ReadingRecord, initialize_database, insert_reading
from .detector import annotate_detection, crop_frame, detect_blue_marker


def _timestamp_slug(now: datetime) -> str:
    return now.strftime("%Y%m%dT%H%M%S.%fZ")


def _dated_directory(base: Path, now: datetime, kind: str) -> Path:
    return base / kind / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")


def _relative_to_data(path: Path, data_dir: Path) -> str:
    return str(path.resolve().relative_to(data_dir.resolve()))


def compute_percent_full(marker_center_y: float | None, empty_y: float, full_y: float) -> float | None:
    if marker_center_y is None:
        return None

    if full_y == empty_y:
        raise ValueError("WELL_FULL_Y and WELL_EMPTY_Y must be different values")

    raw_percent = ((marker_center_y - empty_y) / (full_y - empty_y)) * 100.0
    return max(0.0, min(100.0, raw_percent))


def collect_once(config: AppConfig, sample_image: Path | None = None) -> ReadingRecord:
    config.ensure_dirs()
    initialize_database(config.db_path)

    captured_at = datetime.now(timezone.utc)
    slug = _timestamp_slug(captured_at)
    raw_dir = _dated_directory(config.snapshots_dir, captured_at, "raw")
    crop_dir = _dated_directory(config.snapshots_dir, captured_at, "crop")
    debug_dir = _dated_directory(config.snapshots_dir, captured_at, "debug")
    raw_dir.mkdir(parents=True, exist_ok=True)
    crop_dir.mkdir(parents=True, exist_ok=True)
    if config.save_debug_images:
        debug_dir.mkdir(parents=True, exist_ok=True)

    raw_path = raw_dir / f"{slug}.jpg"
    crop_path = crop_dir / f"{slug}.jpg"
    debug_path = debug_dir / f"{slug}.jpg"

    if sample_image is not None:
        source_kind = ingest_local_image(sample_image, raw_path)
    else:
        source_kind = capture_snapshot(config, raw_path)

    image = cv2.imread(str(raw_path))
    if image is None:
        raise RuntimeError(f"Unable to read captured image at {raw_path}")

    crop = crop_frame(image, config.crop)
    if not cv2.imwrite(str(crop_path), crop):
        raise RuntimeError(f"Unable to write crop image to {crop_path}")

    detection = detect_blue_marker(crop, config)
    percent_full = compute_percent_full(detection.marker_center_y, config.empty_y, config.full_y)

    debug_rel_path: str | None = None
    if config.save_debug_images:
        annotated = annotate_detection(crop, detection)
        if not cv2.imwrite(str(debug_path), annotated):
            raise RuntimeError(f"Unable to write debug image to {debug_path}")
        debug_rel_path = _relative_to_data(debug_path, config.data_dir)

    reading = ReadingRecord(
        captured_at=captured_at.isoformat(),
        source_kind=source_kind,
        raw_image_path=_relative_to_data(raw_path, config.data_dir),
        crop_image_path=_relative_to_data(crop_path, config.data_dir),
        debug_image_path=debug_rel_path,
        marker_found=detection.found,
        marker_center_x=detection.marker_center_x,
        marker_center_y=detection.marker_center_y,
        bbox_x=detection.bbox_x,
        bbox_y=detection.bbox_y,
        bbox_width=detection.bbox_width,
        bbox_height=detection.bbox_height,
        contour_area=detection.contour_area,
        confidence=detection.confidence,
        percent_full=percent_full,
        notes=detection.notes,
    )

    return insert_reading(config.db_path, reading)


def serialize_reading(reading: ReadingRecord | None) -> dict[str, Any] | None:
    if reading is None:
        return None

    payload = asdict(reading)
    payload["raw_image_url"] = f"/data/{reading.raw_image_path}"
    payload["crop_image_url"] = f"/data/{reading.crop_image_path}"
    payload["debug_image_url"] = (
        f"/data/{reading.debug_image_path}" if reading.debug_image_path else None
    )
    return payload
