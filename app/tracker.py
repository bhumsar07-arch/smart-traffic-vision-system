"""Tracking abstractions and per-vehicle trajectory history."""

from __future__ import annotations

from collections import defaultdict, deque

from app.detector import Detection


class TrajectoryTracker:
    """Maintain bounded centroid histories for ByteTrack identities."""

    def __init__(self, history_length: int = 30) -> None:
        """Create a trajectory store with a fixed history capacity."""
        if history_length < 2:
            raise ValueError("history_length must be at least 2")
        self._history_length = history_length
        self._trajectories: dict[int, deque[tuple[int, int]]] = defaultdict(
            lambda: deque(maxlen=self._history_length)
        )

    def update(self, detections: list[Detection]) -> None:
        """Append centroids for observations that have valid track IDs."""
        for detection in detections:
            if detection.track_id is not None:
                self._trajectories[detection.track_id].append(detection.centroid)

    def previous_centroid(self, track_id: int) -> tuple[int, int] | None:
        """Return the penultimate centroid for a tracked vehicle, if available."""
        trajectory = self._trajectories.get(track_id)
        return trajectory[-2] if trajectory and len(trajectory) >= 2 else None

    def prune(self, active_ids: set[int]) -> None:
        """Remove trajectory state for identities no longer active."""
        stale_ids = set(self._trajectories) - active_ids
        for track_id in stale_ids:
            del self._trajectories[track_id]
