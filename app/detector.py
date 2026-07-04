"""YOLOv8 vehicle detection with lazy model initialization."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
from loguru import logger

from app.config import Settings
from app.utils import class_color, draw_label


@dataclass(frozen=True, slots=True)
class Detection:
    """A vehicle detection optionally associated with a tracker identity."""

    bbox: tuple[int, int, int, int]
    confidence: float
    class_id: int
    class_name: str
    track_id: int | None = None

    @property
    def centroid(self) -> tuple[int, int]:
        """Return the bounding-box center point."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) // 2, (y1 + y2) // 2)


class VehicleDetector:
    """Detect supported road vehicles with an Ultralytics YOLOv8 model."""

    def __init__(self, settings: Settings) -> None:
        """Initialize detector configuration without loading model weights."""
        self.settings = settings
        self._model: Any | None = None

    def _load_model(self) -> Any:
        """Load YOLO weights on first inference, allowing graceful API startup."""
        if self._model is None:
            try:
                from ultralytics import YOLO
            except ImportError as exc:
                raise RuntimeError("Ultralytics is not installed. Run: pip install -r requirements.txt") from exc
            logger.info("Loading YOLO model: {}", self.settings.model_name)
            self._model = YOLO(self.settings.model_name)
        return self._model

    def detect_and_track(self, frame: cv2.typing.MatLike) -> list[Detection]:
        """Run YOLO with ByteTrack and return filtered vehicle observations."""
        model = self._load_model()
        results = model.track(
            source=frame,
            persist=True,
            tracker=self.settings.tracker_config,
            conf=self.settings.confidence_threshold,
            iou=self.settings.iou_threshold,
            classes=list(self.settings.vehicle_class_ids),
            verbose=False,
        )
        if not results or results[0].boxes is None:
            return []

        boxes = results[0].boxes
        identities = boxes.id.int().cpu().tolist() if boxes.id is not None else [None] * len(boxes)
        coordinates = boxes.xyxy.int().cpu().tolist()
        confidences = boxes.conf.cpu().tolist()
        class_ids = boxes.cls.int().cpu().tolist()
        names = results[0].names

        detections: list[Detection] = []
        for bbox, confidence, class_id, track_id in zip(coordinates, confidences, class_ids, identities, strict=True):
            detections.append(
                Detection(
                    bbox=tuple(bbox),
                    confidence=float(confidence),
                    class_id=class_id,
                    class_name=str(names[class_id]).lower(),
                    track_id=track_id,
                )
            )
        return detections

    @staticmethod
    def draw_detections(frame: cv2.typing.MatLike, detections: list[Detection]) -> None:
        """Render professional bounding boxes, labels, confidence, and IDs."""
        for detection in detections:
            x1, y1, x2, y2 = detection.bbox
            color = class_color(detection.class_name)
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2, cv2.LINE_AA)
            identity = str(detection.track_id) if detection.track_id is not None else "N/A"
            label = f"{detection.class_name.title()} {detection.confidence:.2f} | ID {identity}"
            draw_label(frame, label, (x1, y1), color)

    @staticmethod
    def resolve_model_path(model_name: str, models_directory: Path) -> str:
        """Prefer a local model file and otherwise permit Ultralytics download."""
        local_path = models_directory / model_name
        return str(local_path) if local_path.exists() else model_name
