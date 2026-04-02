from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .config import AppConfig, CropRect


@dataclass(frozen=True)
class DetectionResult:
    found: bool
    marker_center_x: float | None
    marker_center_y: float | None
    bbox_x: int | None
    bbox_y: int | None
    bbox_width: int | None
    bbox_height: int | None
    contour_area: float | None
    confidence: float
    notes: str


def crop_frame(image: np.ndarray, crop: CropRect) -> np.ndarray:
    image_height, image_width = image.shape[:2]
    x1 = max(0, crop.x)
    y1 = max(0, crop.y)
    x2 = min(image_width, crop.x + crop.width)
    y2 = min(image_height, crop.y + crop.height)

    if x2 <= x1 or y2 <= y1:
        raise ValueError("Configured crop rectangle falls outside the image bounds")

    return image[y1:y2, x1:x2].copy()


def detect_blue_marker(image: np.ndarray, config: AppConfig) -> DetectionResult:
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    lower = np.array(config.blue_hsv_lower, dtype=np.uint8)
    upper = np.array(config.blue_hsv_upper, dtype=np.uint8)

    mask = cv2.inRange(hsv, lower, upper)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_candidate: tuple[float, DetectionResult] | None = None
    image_width = image.shape[1]
    expected_x = config.expected_marker_x if config.expected_marker_x is not None else image_width // 2

    for contour in contours:
        area = cv2.contourArea(contour)
        if area < config.min_contour_area:
            continue

        x, y, width, height = cv2.boundingRect(contour)
        center_x = x + (width / 2.0)
        center_y = y + (height / 2.0)
        aspect_ratio = height / max(width, 1)
        fill_ratio = area / max(width * height, 1)

        area_score = min(area / max(config.min_contour_area * 5, 1), 1.0)
        aspect_score = min(aspect_ratio / 2.5, 1.0) if aspect_ratio >= 1 else max(aspect_ratio, 0.1)
        fill_score = min(fill_ratio / 0.65, 1.0)
        x_score = 1.0 - min(abs(center_x - expected_x) / max(image_width / 2.0, 1.0), 1.0)

        score = (0.35 * area_score) + (0.25 * aspect_score) + (0.15 * fill_score) + (0.25 * x_score)
        confidence = min(0.99, 0.25 + (0.74 * score))

        result = DetectionResult(
            found=True,
            marker_center_x=center_x,
            marker_center_y=center_y,
            bbox_x=x,
            bbox_y=y,
            bbox_width=width,
            bbox_height=height,
            contour_area=float(area),
            confidence=confidence,
            notes=f"Blue contour detected with aspect_ratio={aspect_ratio:.2f} fill_ratio={fill_ratio:.2f}",
        )

        if best_candidate is None or score > best_candidate[0]:
            best_candidate = (score, result)

    if best_candidate is None:
        return DetectionResult(
            found=False,
            marker_center_x=None,
            marker_center_y=None,
            bbox_x=None,
            bbox_y=None,
            bbox_width=None,
            bbox_height=None,
            contour_area=None,
            confidence=0.0,
            notes="No blue contour matched the configured thresholds",
        )

    return best_candidate[1]


def annotate_detection(image: np.ndarray, detection: DetectionResult) -> np.ndarray:
    annotated = image.copy()
    height, width = annotated.shape[:2]

    cv2.line(
        annotated,
        (width // 2, 0),
        (width // 2, height),
        (180, 180, 180),
        1,
    )

    if detection.found and detection.bbox_x is not None:
        top_left = (detection.bbox_x, detection.bbox_y)
        bottom_right = (
            detection.bbox_x + detection.bbox_width,
            detection.bbox_y + detection.bbox_height,
        )
        cv2.rectangle(annotated, top_left, bottom_right, (0, 255, 255), 2)
        cv2.circle(
            annotated,
            (int(detection.marker_center_x), int(detection.marker_center_y)),
            5,
            (0, 0, 255),
            -1,
        )
        label = f"y={detection.marker_center_y:.1f} conf={detection.confidence:.2f}"
        cv2.putText(
            annotated,
            label,
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )
    else:
        cv2.putText(
            annotated,
            "Marker not found",
            (10, 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 255),
            2,
            cv2.LINE_AA,
        )

    return annotated
