"""CSV reporting and chart generation for traffic statistics."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from loguru import logger

from app.database import TrafficDatabase


class TrafficAnalytics:
    """Generate portable reports and presentation-ready charts."""

    def __init__(self, database: TrafficDatabase) -> None:
        """Bind analytics operations to a traffic database."""
        self.database = database

    def _dataframe(self) -> pd.DataFrame:
        """Load chronological database records into a DataFrame."""
        return pd.DataFrame(self.database.all_chronological())

    def export_csv(self, output_path: Path) -> Path:
        """Export records to CSV, using a timestamped file if the target is locked."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frame = self._dataframe()
        try:
            frame.to_csv(output_path, index=False)
            saved_path = output_path
        except PermissionError:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            saved_path = output_path.with_name(f"{output_path.stem}_{timestamp}{output_path.suffix}")
            logger.warning("CSV report is locked; saving this run to {} instead", saved_path)
            frame.to_csv(saved_path, index=False)
        logger.info("CSV report saved to {}", saved_path)
        return saved_path

    def generate_charts(self, output_directory: Path) -> list[Path]:
        """Generate vehicle timeline, density, and type distribution charts."""
        frame = self._dataframe()
        if frame.empty:
            logger.warning("No statistics available; chart generation skipped")
            return []
        output_directory.mkdir(parents=True, exist_ok=True)
        paths = [
            self._vehicle_count_chart(frame, output_directory),
            self._density_chart(frame, output_directory),
            self._vehicle_type_chart(frame, output_directory),
        ]
        logger.info("Generated {} analytics charts", len(paths))
        return paths

    @staticmethod
    def _save_figure(path: Path) -> Path:
        """Apply layout, save the active figure, and release resources."""
        plt.tight_layout()
        plt.savefig(path, dpi=160, bbox_inches="tight")
        plt.close()
        return path

    def _vehicle_count_chart(self, frame: pd.DataFrame, directory: Path) -> Path:
        """Plot visible vehicle count over processed frames."""
        plt.figure(figsize=(12, 5))
        plt.plot(frame.index, frame["vehicle_count"], color="#1976D2", linewidth=1.5)
        plt.title("Vehicle Count Over Time")
        plt.xlabel("Frame")
        plt.ylabel("Visible Vehicles")
        plt.grid(alpha=0.25)
        return self._save_figure(directory / "vehicle_count_over_time.png")

    def _density_chart(self, frame: pd.DataFrame, directory: Path) -> Path:
        """Plot the distribution of density classifications."""
        order = ["LOW", "MEDIUM", "HIGH"]
        values = frame["density"].value_counts().reindex(order, fill_value=0)
        plt.figure(figsize=(8, 5))
        plt.bar(order, values, color=["#43A047", "#FB8C00", "#E53935"])
        plt.title("Density Distribution")
        plt.xlabel("Density")
        plt.ylabel("Frames")
        return self._save_figure(directory / "density_distribution.png")

    def _vehicle_type_chart(self, frame: pd.DataFrame, directory: Path) -> Path:
        """Plot final cumulative counts by normalized vehicle category."""
        final = frame.iloc[-1]
        labels = ["Cars", "Bikes", "Buses", "Trucks"]
        values = [final["cars"], final["bikes"], final["buses"], final["trucks"]]
        plt.figure(figsize=(8, 5))
        plt.bar(labels, values, color=["#2E7D32", "#F9A825", "#7B1FA2", "#C62828"])
        plt.title("Vehicle Type Distribution")
        plt.xlabel("Vehicle Type")
        plt.ylabel("Crossing Count")
        return self._save_figure(directory / "vehicle_type_distribution.png")
