"""Unit tests for analytics report generation."""

from pathlib import Path

from app.analytics import TrafficAnalytics


class LockedOnceFrame:
    """Mimic a DataFrame whose configured output is locked by another program."""

    def __init__(self, locked_path: Path) -> None:
        self.locked_path = locked_path
        self.saved_paths: list[Path] = []

    def to_csv(self, path: Path, index: bool) -> None:
        """Reject the locked path and allow the timestamped fallback."""
        assert index is False
        path = Path(path)
        if path == self.locked_path:
            raise PermissionError("file is locked")
        path.write_text("vehicle_count\n1\n", encoding="utf-8")
        self.saved_paths.append(path)


def test_export_csv_uses_timestamped_fallback_when_target_is_locked(tmp_path: Path) -> None:
    """Complete report export even when Excel has the standard CSV open."""
    output_path = tmp_path / "traffic_report.csv"
    frame = LockedOnceFrame(output_path)
    analytics = TrafficAnalytics(database=None)  # type: ignore[arg-type]
    analytics._dataframe = lambda: frame  # type: ignore[method-assign, return-value]

    saved_path = analytics.export_csv(output_path)

    assert saved_path != output_path
    assert saved_path.match("traffic_report_*.csv")
    assert saved_path.read_text(encoding="utf-8") == "vehicle_count\n1\n"
