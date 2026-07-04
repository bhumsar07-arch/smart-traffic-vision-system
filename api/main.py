"""FastAPI service exposing persisted traffic statistics."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import FastAPI, Query
from pydantic import BaseModel, ConfigDict

from app.config import get_settings
from app.database import TrafficDatabase


class StatisticsResponse(BaseModel):
    """Public representation of one stored traffic statistics record."""

    model_config = ConfigDict(extra="ignore")
    id: int
    timestamp: str
    vehicle_count: int
    cars: int
    bikes: int
    buses: int
    trucks: int
    density: Literal["LOW", "MEDIUM", "HIGH"]
    green_signal_time: int


class HealthResponse(BaseModel):
    """Service health response contract."""

    status: Literal["healthy"]
    service: str


settings = get_settings()
database = TrafficDatabase(settings.database_path)
app = FastAPI(
    title="VisionTrafficAI API",
    description="Traffic density and adaptive signal statistics API",
    version="1.0.0",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    """Return service readiness status."""
    return HealthResponse(status="healthy", service="VisionTrafficAI")


@app.get("/stats", response_model=StatisticsResponse | None, tags=["traffic"])
def latest_stats() -> dict[str, object] | None:
    """Return the latest processed frame statistics."""
    return database.latest()


@app.get("/history", response_model=list[StatisticsResponse], tags=["traffic"])
def history(
    limit: Annotated[int, Query(ge=1, le=10_000)] = settings.api_history_limit,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[dict[str, object]]:
    """Return paginated statistics in reverse chronological order."""
    return database.history(limit=limit, offset=offset)
