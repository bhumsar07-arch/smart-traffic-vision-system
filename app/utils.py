"""Reusable utilities for logging, drawing, and video metadata."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import cv2
from loguru import logger

from app.config import Settings


CLASS_COLORS: Final[dict[str, tuple[int, int, int]]] = {
    "car": (36, 180, 76),
    "motorcycle": (0, 165, 255),
    "bicycle": (255, 170, 0),
    "bus": (196, 84, 255),
    "truck": (70, 70, 255),
}


@dataclass(frozen=True, slots=True)
class VideoMetadata:
    """Video stream properties required to configure output writing."""

    width: int
    height: int
    fps: float
    frame_count: int


def configure_logging(settings: Settings) -> None:
    """Configure structured application logging to stderr and a rotating file."""
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level, colorize=True)
    log_path = settings.output_video_path.parent / "vision_traffic_ai.log"
    logger.add(log_path, level=settings.log_level, rotation="10 MB", retention="7 days")


def validate_video_path(path: Path) -> None:
    """Raise a descriptive error when a source video cannot be used."""
    if not path.exists():
        raise FileNotFoundError(
            f"Input video not found: {path}. Place traffic.mp4 in the videos folder "
            "or pass --video with a valid file."
        )
    if not path.is_file():
        raise ValueError(f"Input video path is not a file: {path}")


def get_video_metadata(capture: cv2.VideoCapture) -> VideoMetadata:
    """Extract and validate video metadata from an open capture."""
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = float(capture.get(cv2.CAP_PROP_FPS))
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if width <= 0 or height <= 0:
        raise ValueError("Video has invalid dimensions")
    if fps <= 0:
        logger.warning("Video reports invalid FPS; falling back to 30 FPS")
        fps = 30.0
    return VideoMetadata(width=width, height=height, fps=fps, frame_count=frame_count)


def draw_label(
    frame: cv2.typing.MatLike,
    text: str,
    origin: tuple[int, int],
    color: tuple[int, int, int],
    scale: float = 0.55,
) -> None:
    """Draw a readable filled label on a video frame."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    thickness = 1
    (width, height), baseline = cv2.getTextSize(text, font, scale, thickness)
    x, y = origin
    y = max(y, height + baseline + 4)
    cv2.rectangle(frame, (x, y - height - baseline - 6), (x + width + 8, y), color, -1)
    cv2.putText(frame, text, (x + 4, y - baseline - 3), font, scale, (255, 255, 255), thickness, cv2.LINE_AA)


def class_color(class_name: str) -> tuple[int, int, int]:
    """Return the configured BGR drawing color for a vehicle class."""
    return CLASS_COLORS.get(class_name.lower(), (255, 255, 255))
