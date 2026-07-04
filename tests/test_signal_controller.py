"""Unit tests for adaptive signal timing."""

import pytest

from app.density import DensityLevel
from app.signal_controller import AdaptiveSignalController


@pytest.mark.parametrize(
    ("density", "expected"),
    [(DensityLevel.LOW, 20), (DensityLevel.MEDIUM, 40), (DensityLevel.HIGH, 60)],
)
def test_signal_recommendations(density: DensityLevel, expected: int) -> None:
    """Map each density category to its configured duration."""
    assert AdaptiveSignalController().recommend(density) == expected


def test_non_monotonic_durations_rejected() -> None:
    """Reject signal policies that allocate less time to denser traffic."""
    with pytest.raises(ValueError):
        AdaptiveSignalController(30, 20, 60)
