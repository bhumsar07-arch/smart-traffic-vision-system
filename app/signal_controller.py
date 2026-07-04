"""Adaptive traffic signal recommendation policy."""

from __future__ import annotations

from app.density import DensityLevel


class AdaptiveSignalController:
    """Map traffic density to an appropriate green-signal duration."""

    def __init__(self, low_seconds: int = 20, medium_seconds: int = 40, high_seconds: int = 60) -> None:
        """Initialize density timing policy."""
        if min(low_seconds, medium_seconds, high_seconds) <= 0:
            raise ValueError("Signal durations must be positive")
        if not low_seconds <= medium_seconds <= high_seconds:
            raise ValueError("Signal durations must be monotonically increasing")
        self._durations = {
            DensityLevel.LOW: low_seconds,
            DensityLevel.MEDIUM: medium_seconds,
            DensityLevel.HIGH: high_seconds,
        }

    def recommend(self, density: DensityLevel) -> int:
        """Return recommended green-signal time in seconds."""
        try:
            return self._durations[density]
        except KeyError as exc:
            raise ValueError(f"Unsupported density level: {density}") from exc
