"""Unit tests for virtual-line vehicle counting."""

from app.counter import VehicleCounter
from app.detector import Detection


def observation(track_id: int, class_name: str, center_y: int) -> Detection:
    """Create a compact test observation centered at the requested y value."""
    return Detection(
        bbox=(0, center_y - 5, 10, center_y + 5),
        confidence=0.9,
        class_id=2,
        class_name=class_name,
        track_id=track_id,
    )


def test_crossing_counts_vehicle_once() -> None:
    """Count one tracked car once even if it crosses the line repeatedly."""
    counter = VehicleCounter(line_y=100, tolerance=2)
    counter.update([observation(7, "car", 80)])
    assert counter.update([observation(7, "car", 105)]) == [7]
    counter.update([observation(7, "car", 80)])
    assert counter.counts.cars == 1
    assert counter.counts.total == 1


def test_motorcycles_and_bicycles_share_bike_category() -> None:
    """Normalize both supported two-wheeler classes into bikes."""
    counter = VehicleCounter(line_y=100)
    counter.update([observation(1, "motorcycle", 70), observation(2, "bicycle", 70)])
    counter.update([observation(1, "motorcycle", 110), observation(2, "bicycle", 110)])
    assert counter.counts.bikes == 2


def test_missing_identity_is_ignored() -> None:
    """Avoid double counting detections for which tracking has no identity."""
    counter = VehicleCounter(line_y=100)
    detection = Detection((0, 90, 10, 100), 0.8, 2, "car", None)
    assert counter.update([detection]) == []
    assert counter.counts.total == 0
