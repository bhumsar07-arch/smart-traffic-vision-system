"""Application configuration and filesystem path management."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator


PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]


class Settings(BaseModel):
    """Validated application settings shared by all components."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    project_root: Path = PROJECT_ROOT
    video_path: Path = PROJECT_ROOT / "videos" / "traffic.mp4"
    output_video_path: Path = PROJECT_ROOT / "outputs" / "processed_traffic.mp4"
    database_path: Path = PROJECT_ROOT / "data" / "traffic_stats.db"
    csv_report_path: Path = PROJECT_ROOT / "outputs" / "traffic_report.csv"
    charts_directory: Path = PROJECT_ROOT / "outputs" / "charts"
    model_name: str = "yolov8n.pt"
    confidence_threshold: float = Field(default=0.35, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    tracker_config: str = "bytetrack.yaml"
    counting_line_ratio: float = Field(default=0.60, gt=0.0, lt=1.0)
    crossing_tolerance_pixels: int = Field(default=8, ge=0)
    low_density_max: int = Field(default=5, ge=0)
    medium_density_max: int = Field(default=15, ge=1)
    low_green_seconds: int = Field(default=20, gt=0)
    medium_green_seconds: int = Field(default=40, gt=0)
    high_green_seconds: int = Field(default=60, gt=0)
    api_history_limit: int = Field(default=500, gt=0, le=10_000)
    vehicle_class_ids: tuple[int, ...] = (1, 2, 3, 5, 7)
    display_window: bool = False
    log_level: str = "INFO"

    @field_validator("medium_density_max")
    @classmethod
    def validate_density_thresholds(cls, value: int, info: object) -> int:
        """Ensure the medium threshold is greater than the low threshold."""
        data = getattr(info, "data", {})
        if value <= data.get("low_density_max", 5):
            raise ValueError("medium_density_max must exceed low_density_max")
        return value

    def create_directories(self) -> None:
        """Create all runtime directories if they do not already exist."""
        for path in (
            self.video_path.parent,
            self.output_video_path.parent,
            self.database_path.parent,
            self.csv_report_path.parent,
            self.charts_directory,
        ):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached immutable application settings instance."""
    settings = Settings()
    settings.create_directories()
    return settings
