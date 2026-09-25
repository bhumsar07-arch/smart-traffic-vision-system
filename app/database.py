"""SQLite persistence for frame-level traffic statistics."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass(frozen=True, slots=True)
class FrameStatistics:
    """Statistics captured for a processed video frame."""

    timestamp: str
    vehicle_count: int
    cars: int
    bikes: int
    buses: int
    trucks: int
    density: str
    green_signal_time: int

    @classmethod
    def now(
        cls,
        vehicle_count: int,
        cars: int,
        bikes: int,
        buses: int,
        trucks: int,
        density: str,
        green_signal_time: int,
    ) -> "FrameStatistics":
        """Construct a statistics record using the current UTC timestamp."""
        return cls(
            timestamp=datetime.now(timezone.utc).isoformat(),
            vehicle_count=vehicle_count,
            cars=cars,
            bikes=bikes,
            buses=buses,
            trucks=trucks,
            density=density,
            green_signal_time=green_signal_time,
        )


class TrafficDatabase:
    """Manage resilient SQLite storage with parameterized statements."""

    def __init__(self, path: Path) -> None:
        """Initialize the database path and create its schema."""
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a row-enabled SQLite connection and close it safely."""
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        """Create the statistics table and timestamp index when absent."""
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode=WAL;")
            connection.execute("PRAGMA synchronous=NORMAL;")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS traffic_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    vehicle_count INTEGER NOT NULL CHECK(vehicle_count >= 0),
                    cars INTEGER NOT NULL CHECK(cars >= 0),
                    bikes INTEGER NOT NULL CHECK(bikes >= 0),
                    buses INTEGER NOT NULL CHECK(buses >= 0),
                    trucks INTEGER NOT NULL CHECK(trucks >= 0),
                    density TEXT NOT NULL CHECK(density IN ('LOW', 'MEDIUM', 'HIGH')),
                    green_signal_time INTEGER NOT NULL CHECK(green_signal_time > 0)
                );
                CREATE INDEX IF NOT EXISTS idx_traffic_timestamp
                ON traffic_statistics(timestamp DESC);
                """
            )

    def insert(self, statistics: FrameStatistics) -> int:
        """Insert one frame record and return its generated identifier."""
        values = asdict(statistics)
        with self._connection() as connection:
            cursor = connection.execute(
                """INSERT INTO traffic_statistics
                (timestamp, vehicle_count, cars, bikes, buses, trucks, density, green_signal_time)
                VALUES (:timestamp, :vehicle_count, :cars, :bikes, :buses, :trucks, :density, :green_signal_time)""",
                values,
            )
            return int(cursor.lastrowid or 0)

    def insert_batch(self, statistics_list: list[FrameStatistics]) -> None:
        """Insert multiple frame records in a single atomic transaction."""
        if not statistics_list:
            return
        values = [asdict(record) for record in statistics_list]
        with self._connection() as connection:
            connection.executemany(
                """INSERT INTO traffic_statistics
                (timestamp, vehicle_count, cars, bikes, buses, trucks, density, green_signal_time)
                VALUES (:timestamp, :vehicle_count, :cars, :bikes, :buses, :trucks, :density, :green_signal_time)""",
                values,
            )

    def latest(self) -> dict[str, object] | None:
        """Return the newest statistics record or None for an empty database."""
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM traffic_statistics ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def history(self, limit: int = 500, offset: int = 0) -> list[dict[str, object]]:
        """Return recent records in reverse chronological order."""
        if limit <= 0 or offset < 0:
            raise ValueError("limit must be positive and offset cannot be negative")
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM traffic_statistics ORDER BY id DESC LIMIT ? OFFSET ?", (limit, offset)
            ).fetchall()
        return [dict(row) for row in rows]

    def all_chronological(self) -> list[dict[str, object]]:
        """Return all statistics records ordered for report generation."""
        with self._connection() as connection:
            rows = connection.execute("SELECT * FROM traffic_statistics ORDER BY id ASC").fetchall()
        return [dict(row) for row in rows]
