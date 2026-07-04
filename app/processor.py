"""End-to-end video processing orchestration."""

from __future__ import annotations

from pathlib import Path

import cv2
from loguru import logger

from app.analytics import TrafficAnalytics
from app.config import Settings
from app.counter import VehicleCounter
from app.database import FrameStatistics, TrafficDatabase
from app.density import DensityEstimator, DensityLevel
from app.detector import VehicleDetector
from app.signal_controller import AdaptiveSignalController
from app.tracker import TrajectoryTracker
from app.utils import draw_label, get_video_metadata, validate_video_path


class TrafficVideoProcessor:
    """Coordinate inference, counting, annotation, persistence, and reporting."""

    def __init__(self, settings: Settings) -> None:
        """Build processing dependencies from validated settings."""
        self.settings = settings
        model = VehicleDetector.resolve_model_path(settings.model_name, settings.project_root / "models")
        detector_settings = settings.model_copy(update={"model_name": model})
        self.detector = VehicleDetector(detector_settings)
        self.density_estimator = DensityEstimator(settings.low_density_max, settings.medium_density_max)
        self.signal_controller = AdaptiveSignalController(
            settings.low_green_seconds, settings.medium_green_seconds, settings.high_green_seconds
        )
        self.database = TrafficDatabase(settings.database_path)
        self.analytics = TrafficAnalytics(self.database)
        self.trajectory_tracker = TrajectoryTracker()

    def process(self, video_path: Path | None = None) -> Path:
        """Process a traffic video and return the annotated output path."""
        source = video_path or self.settings.video_path
        validate_video_path(source)
        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            capture.release()
            raise RuntimeError(f"OpenCV could not open video: {source}")

        writer: cv2.VideoWriter | None = None
        try:
            metadata = get_video_metadata(capture)
            line_y = int(metadata.height * self.settings.counting_line_ratio)
            counter = VehicleCounter(line_y, self.settings.crossing_tolerance_pixels)
            self.settings.output_video_path.parent.mkdir(parents=True, exist_ok=True)
            writer = cv2.VideoWriter(
                str(self.settings.output_video_path),
                cv2.VideoWriter_fourcc(*"mp4v"),
                metadata.fps,
                (metadata.width, metadata.height),
            )
            if not writer.isOpened():
                raise RuntimeError(f"Could not create output video: {self.settings.output_video_path}")
            self._process_frames(capture, writer, counter, line_y, metadata.frame_count)
        finally:
            capture.release()
            if writer is not None:
                writer.release()
            cv2.destroyAllWindows()

        self.analytics.export_csv(self.settings.csv_report_path)
        self.analytics.generate_charts(self.settings.charts_directory)
        logger.success("Processing complete: {}", self.settings.output_video_path)
        return self.settings.output_video_path

    def _process_frames(
        self,
        capture: cv2.VideoCapture,
        writer: cv2.VideoWriter,
        counter: VehicleCounter,
        line_y: int,
        total_frames: int,
    ) -> None:
        """Process all readable frames and persist each resulting observation."""
        frame_number = 0
        while True:
            success, frame = capture.read()
            if not success:
                break
            frame_number += 1
            detections = self.detector.detect_and_track(frame)
            self.trajectory_tracker.update(detections)
            counter.update(detections)
            density = self.density_estimator.calculate(len(detections))
            green_seconds = self.signal_controller.recommend(density)
            self.detector.draw_detections(frame, detections)
            self._draw_dashboard(frame, counter, line_y, len(detections), density, green_seconds)
            counts = counter.counts
            self.database.insert(
                FrameStatistics.now(
                    vehicle_count=len(detections),
                    cars=counts.cars,
                    bikes=counts.bikes,
                    buses=counts.buses,
                    trucks=counts.trucks,
                    density=density.value,
                    green_signal_time=green_seconds,
                )
            )
            writer.write(frame)
            if frame_number % 100 == 0:
                logger.info("Processed {}/{} frames", frame_number, total_frames or "unknown")
            if self.settings.display_window:
                cv2.imshow("VisionTrafficAI", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    logger.info("Processing stopped by user")
                    break

    @staticmethod
    def _draw_dashboard(
        frame: cv2.typing.MatLike,
        counter: VehicleCounter,
        line_y: int,
        visible_count: int,
        density: DensityLevel,
        green_seconds: int,
    ) -> None:
        """Draw counting line and compact traffic metrics overlay."""
        width = frame.shape[1]
        cv2.line(frame, (0, line_y), (width, line_y), (0, 255, 255), 2, cv2.LINE_AA)
        draw_label(frame, "COUNTING LINE", (12, line_y - 4), (0, 180, 180), 0.5)
        counts = counter.counts
        density_colors = {
            DensityLevel.LOW: (40, 170, 60),
            DensityLevel.MEDIUM: (0, 150, 255),
            DensityLevel.HIGH: (30, 30, 220),
        }
        cv2.rectangle(frame, (10, 10), (390, 138), (20, 20, 20), -1)
        cv2.rectangle(frame, (10, 10), (390, 138), (220, 220, 220), 1)
        lines = [
            f"VISIBLE VEHICLES: {visible_count}",
            f"DENSITY: {density.value}",
            f"GREEN SIGNAL: {green_seconds} sec",
            f"CROSSED | Cars {counts.cars}  Bikes {counts.bikes}  Bus {counts.buses}  Truck {counts.trucks}",
        ]
        for index, text in enumerate(lines):
            color = density_colors[density] if index == 1 else (245, 245, 245)
            cv2.putText(frame, text, (24, 38 + index * 29), cv2.FONT_HERSHEY_SIMPLEX, 0.58, color, 1, cv2.LINE_AA)
