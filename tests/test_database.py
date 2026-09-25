"""Unit tests for SQLite database persistence."""

from pathlib import Path
import pytest
import sqlite3

from app.database import FrameStatistics, TrafficDatabase


def test_database_insert_and_latest(tmp_path: Path) -> None:
    """Insert a record and retrieve it via latest()."""
    db_path = tmp_path / "test_traffic.db"
    db = TrafficDatabase(db_path)

    assert db.latest() is None

    record = FrameStatistics.now(
        vehicle_count=5,
        cars=3,
        bikes=1,
        buses=1,
        trucks=0,
        density="LOW",
        green_signal_time=20,
    )
    row_id = db.insert(record)
    assert row_id == 1

    latest = db.latest()
    assert latest is not None
    assert latest["vehicle_count"] == 5
    assert latest["density"] == "LOW"
    assert latest["green_signal_time"] == 20


def test_database_insert_batch_and_history(tmp_path: Path) -> None:
    """Insert multiple records in batch and verify pagination."""
    db_path = tmp_path / "test_traffic.db"
    db = TrafficDatabase(db_path)

    records = [
        FrameStatistics.now(
            vehicle_count=i,
            cars=i,
            bikes=0,
            buses=0,
            trucks=0,
            density="LOW" if i <= 5 else "MEDIUM",
            green_signal_time=20 if i <= 5 else 40,
        )
        for i in range(1, 11)
    ]
    db.insert_batch(records)

    history = db.history(limit=5, offset=0)
    assert len(history) == 5
    # Reverse chronological order
    assert history[0]["vehicle_count"] == 10
    assert history[4]["vehicle_count"] == 6

    offset_history = db.history(limit=5, offset=5)
    assert len(offset_history) == 5
    assert offset_history[0]["vehicle_count"] == 5


def test_database_constraints_enforced(tmp_path: Path) -> None:
    """Ensure invalid density or negative vehicle count triggers integrity error."""
    db_path = tmp_path / "test_traffic.db"
    db = TrafficDatabase(db_path)

    invalid_density = FrameStatistics(
        timestamp="2026-09-25T14:00:00",
        vehicle_count=2,
        cars=2,
        bikes=0,
        buses=0,
        trucks=0,
        density="SUPER_HIGH",  # Invalid density
        green_signal_time=30,
    )
    with pytest.raises(sqlite3.IntegrityError):
        db.insert(invalid_density)
