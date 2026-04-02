from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass
class ReadingRecord:
    captured_at: str
    source_kind: str
    raw_image_path: str
    crop_image_path: str
    debug_image_path: str | None
    marker_found: bool
    marker_center_x: float | None
    marker_center_y: float | None
    bbox_x: int | None
    bbox_y: int | None
    bbox_width: int | None
    bbox_height: int | None
    contour_area: float | None
    confidence: float
    percent_full: float | None
    notes: str
    detector_version: str = "opencv-blue-threshold-v1"
    id: int | None = None


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database(db_path: Path) -> None:
    with connect(db_path) as connection:
        connection.execute(
            """
            create table if not exists readings (
              id integer primary key autoincrement,
              captured_at text not null,
              source_kind text not null,
              raw_image_path text not null,
              crop_image_path text not null,
              debug_image_path text,
              marker_found integer not null,
              marker_center_x real,
              marker_center_y real,
              bbox_x integer,
              bbox_y integer,
              bbox_width integer,
              bbox_height integer,
              contour_area real,
              confidence real not null,
              percent_full real,
              notes text not null,
              detector_version text not null,
              created_at text not null default current_timestamp
            )
            """
        )
        connection.execute(
            "create index if not exists idx_readings_captured_at on readings (captured_at desc)"
        )


def insert_reading(db_path: Path, reading: ReadingRecord) -> ReadingRecord:
    with connect(db_path) as connection:
        cursor = connection.execute(
            """
            insert into readings (
              captured_at,
              source_kind,
              raw_image_path,
              crop_image_path,
              debug_image_path,
              marker_found,
              marker_center_x,
              marker_center_y,
              bbox_x,
              bbox_y,
              bbox_width,
              bbox_height,
              contour_area,
              confidence,
              percent_full,
              notes,
              detector_version
            ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
              reading.captured_at,
              reading.source_kind,
              reading.raw_image_path,
              reading.crop_image_path,
              reading.debug_image_path,
              int(reading.marker_found),
              reading.marker_center_x,
              reading.marker_center_y,
              reading.bbox_x,
              reading.bbox_y,
              reading.bbox_width,
              reading.bbox_height,
              reading.contour_area,
              reading.confidence,
              reading.percent_full,
              reading.notes,
              reading.detector_version,
            ),
        )
        reading.id = int(cursor.lastrowid)
    return reading


def _row_to_record(row: sqlite3.Row | None) -> ReadingRecord | None:
    if row is None:
        return None

    return ReadingRecord(
        id=row["id"],
        captured_at=row["captured_at"],
        source_kind=row["source_kind"],
        raw_image_path=row["raw_image_path"],
        crop_image_path=row["crop_image_path"],
        debug_image_path=row["debug_image_path"],
        marker_found=bool(row["marker_found"]),
        marker_center_x=row["marker_center_x"],
        marker_center_y=row["marker_center_y"],
        bbox_x=row["bbox_x"],
        bbox_y=row["bbox_y"],
        bbox_width=row["bbox_width"],
        bbox_height=row["bbox_height"],
        contour_area=row["contour_area"],
        confidence=row["confidence"],
        percent_full=row["percent_full"],
        notes=row["notes"],
        detector_version=row["detector_version"],
    )


def fetch_latest_reading(db_path: Path) -> ReadingRecord | None:
    with connect(db_path) as connection:
        row = connection.execute(
            "select * from readings order by captured_at desc, id desc limit 1"
        ).fetchone()
    return _row_to_record(row)


def fetch_recent_readings(db_path: Path, limit: int = 96) -> list[ReadingRecord]:
    with connect(db_path) as connection:
        rows = connection.execute(
            "select * from readings order by captured_at desc, id desc limit ?",
            (limit,),
        ).fetchall()
    return [record for row in rows if (record := _row_to_record(row)) is not None]


def fetch_recent_summary(db_path: Path, hours: int = 24) -> dict[str, Any]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    with connect(db_path) as connection:
        row = connection.execute(
            """
            select
              count(*) as reading_count,
              avg(percent_full) as avg_percent_full,
              min(percent_full) as min_percent_full,
              max(percent_full) as max_percent_full,
              avg(confidence) as avg_confidence
            from readings
            where captured_at >= ?
            """,
            (cutoff,),
        ).fetchone()

    return {
        "window_hours": hours,
        "reading_count": row["reading_count"] if row else 0,
        "avg_percent_full": row["avg_percent_full"] if row else None,
        "min_percent_full": row["min_percent_full"] if row else None,
        "max_percent_full": row["max_percent_full"] if row else None,
        "avg_confidence": row["avg_confidence"] if row else None,
    }


def delete_all_readings(db_path: Path) -> int:
    with connect(db_path) as connection:
        cursor = connection.execute("delete from readings")
        deleted_count = int(cursor.rowcount or 0)
        connection.execute("delete from sqlite_sequence where name = 'readings'")
    return deleted_count
