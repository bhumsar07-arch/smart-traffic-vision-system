"""Virtual-line vehicle counting logic."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from app.detector import Detection


@dataclass(frozen=True, slots=True)
class VehicleCounts:
    """Normalized cumulative vehicle counts for reporting."""

    cars: int = 0
    bikes: int = 0
    buses: int = 0
    trucks: int = 0

    @property
    def total(self) -> int:
        """Return the total number of counted vehicles."""
        return self.cars + self.bikes + self.buses + self.trucks


class VehicleCounter:
    """Count each tracked vehicle once when it crosses a horizontal line."""

    CATEGORY_MAP = {"car": "cars", "bicycle": "bikes", "motorcycle": "bikes", "bus": "buses", "truck": "trucks"}

    def __init__(self, line_y: int, tolerance: int = 8) -> None:
        """Create a counter for a horizontal line at the supplied y coordinate."""
        if line_y < 0 or tolerance < 0:
            raise ValueError("line_y and tolerance must be non-negative")
        self.line_y = line_y
        self.tolerance = tolerance
        self._previous_y: dict[int, int] = {}
        self._counted_ids: set[int] = set()
        self._counts: Counter[str] = Counter()

    def update(self, detections: list[Detection]) -> list[int]:
        """Update tracking positions and return IDs newly counted this frame."""
        crossed: list[int] = []
        for detection in detections:
            if detection.track_id is None or detection.class_name not in self.CATEGORY_MAP:
                continue
            current_y = detection.centroid[1]
            previous_y = self._previous_y.get(detection.track_id)
            if (
                previous_y is not None
                and detection.track_id not in self._counted_ids
                and self._crossed_line(previous_y, current_y)
            ):
                category = self.CATEGORY_MAP[detection.class_name]
                self._counts[category] += 1
                self._counted_ids.add(detection.track_id)
                crossed.append(detection.track_id)
            self._previous_y[detection.track_id] = current_y
        return crossed

    def _crossed_line(self, previous_y: int, current_y: int) -> bool:
        """Return whether motion traversed the configured counting line."""
        upper = self.line_y - self.tolerance
        lower = self.line_y + self.tolerance
        return (previous_y < upper and current_y >= upper) or (previous_y > lower and current_y <= lower)

    @property
    def counts(self) -> VehicleCounts:
        """Return an immutable snapshot of cumulative counts."""
        return VehicleCounts(
            cars=self._counts["cars"],
            bikes=self._counts["bikes"],
            buses=self._counts["buses"],
            trucks=self._counts["trucks"],
        )
