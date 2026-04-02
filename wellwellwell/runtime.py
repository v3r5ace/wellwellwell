from __future__ import annotations

import logging
import math
import threading
import time

from .config import AppConfig
from .service import collect_once

logger = logging.getLogger("wellwellwell.runtime")


class CollectorLoop:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run,
            name="wellwellwell-collector-loop",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 10.0) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def join(self) -> None:
        if self._thread is not None:
            self._thread.join()

    def _run(self) -> None:
        interval_seconds = max(60, self.config.collect_interval_minutes * 60)

        if self.config.collect_on_startup:
            self._collect_once()

        while not self._stop_event.is_set():
            sleep_seconds = self._seconds_until_next_boundary(interval_seconds)
            logger.info("Next collection scheduled in %.1f seconds", sleep_seconds)
            if self._stop_event.wait(timeout=sleep_seconds):
                break
            self._collect_once()

    def _collect_once(self) -> None:
        try:
            reading = collect_once(self.config)
            logger.info(
                "Collected reading id=%s found=%s percent_full=%s confidence=%.2f",
                reading.id,
                reading.marker_found,
                "null" if reading.percent_full is None else f"{reading.percent_full:.1f}",
                reading.confidence,
            )
        except Exception:  # pragma: no cover - operational logging path
            logger.exception("Collection attempt failed")

    @staticmethod
    def _seconds_until_next_boundary(interval_seconds: int) -> float:
        now = time.time()
        next_boundary = math.floor(now / interval_seconds) * interval_seconds + interval_seconds
        return max(1.0, next_boundary - now)
