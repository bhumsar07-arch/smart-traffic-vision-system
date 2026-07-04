"""Traffic-density classification policies."""

from __future__ import annotations

from enum import StrEnum


class DensityLevel(StrEnum):
    """Supported traffic-density categories."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class DensityEstimator:
    """Classify traffic volume using configurable inclusive thresholds."""

    def __init__(self, low_max: int = 5, medium_max: int = 15) -> None:
        """Initialize and validate density boundaries."""
        if low_max < 0 or medium_max <= low_max:
            raise ValueError("Density thresholds must satisfy 0 <= low_max < medium_max")
        self.low_max = low_max
        self.medium_max = medium_max

    def calculate(self, vehicle_count: int) -> DensityLevel:
        """Return density for the number of vehicles visible in one frame."""
        if vehicle_count < 0:
            raise ValueError("vehicle_count cannot be negative")
        if vehicle_count <= self.low_max:
            return DensityLevel.LOW
        if vehicle_count <= self.medium_max:
            return DensityLevel.MEDIUM
        return DensityLevel.HIGH
