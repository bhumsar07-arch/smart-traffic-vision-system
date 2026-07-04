"""Unit tests for density classification."""

import pytest

from app.density import DensityEstimator, DensityLevel


@pytest.fixture
def estimator() -> DensityEstimator:
    """Provide the default density estimator."""
    return DensityEstimator(low_max=5, medium_max=15)


@pytest.mark.parametrize(
    ("count", "expected"),
    [(0, DensityLevel.LOW), (5, DensityLevel.LOW), (6, DensityLevel.MEDIUM), (15, DensityLevel.MEDIUM), (16, DensityLevel.HIGH)],
)
def test_density_boundaries(estimator: DensityEstimator, count: int, expected: DensityLevel) -> None:
    """Classify exact threshold boundaries correctly."""
    assert estimator.calculate(count) is expected


def test_negative_count_rejected(estimator: DensityEstimator) -> None:
    """Reject logically invalid negative traffic volumes."""
    with pytest.raises(ValueError):
        estimator.calculate(-1)
