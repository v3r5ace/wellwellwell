from __future__ import annotations

import base64
import shutil
import subprocess
import urllib.request
from pathlib import Path

from .config import AppConfig


def capture_snapshot(config: AppConfig, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if config.camera_snapshot_url:
        request = urllib.request.Request(config.camera_snapshot_url)

        if config.camera_username and config.camera_password:
            token = base64.b64encode(
                f"{config.camera_username}:{config.camera_password}".encode("utf-8")
            ).decode("ascii")
            request.add_header("Authorization", f"Basic {token}")

        with urllib.request.urlopen(request, timeout=20) as response, destination.open("wb") as handle:
            handle.write(response.read())
        return "snapshot_url"

    if config.camera_rtsp_url:
        command = [
            config.ffmpeg_path,
            "-hide_banner",
            "-loglevel",
            "error",
            "-rtsp_transport",
            config.ffmpeg_rtsp_transport,
            "-y",
            "-i",
            config.camera_rtsp_url,
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(destination),
        ]

        try:
            completed = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=config.ffmpeg_capture_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(
                "Timed out while connecting to the camera stream. "
                "Check CAMERA_RTSP_URL, network reachability from the container, and ffmpeg transport settings."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = (exc.stderr or "").strip()
            raise RuntimeError(
                "ffmpeg could not capture a frame from the camera stream. "
                f"stderr: {stderr or 'no stderr output'}"
            ) from exc

        if not destination.exists():
            stderr = (completed.stderr or "").strip()
            raise RuntimeError(
                "ffmpeg exited without producing a snapshot. "
                f"stderr: {stderr or 'no stderr output'}"
            )

        return "rtsp"

    raise RuntimeError("Set CAMERA_SNAPSHOT_URL or CAMERA_RTSP_URL before collecting a live reading")


def ingest_local_image(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return "file"
