"""JSON API for the calendar, the series, and the monthly heatmap."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from brasa.config import ASSUMPTIONS_ES, GRID_DEGREES, TRANSITION_YEAR
from brasa.regions import REGIONS, USE_CASES
from brasa.services.query import QueryError, build_view, resolve_area

router = APIRouter()


class QueryBody(BaseModel):
    region_id: str | None = None
    bbox: list[float] | None = None
    polygon: list[list[float]] | None = Field(default=None, description="Vertices as [lon, lat]")
    year: int = 2022
    month: int = 7
    sensor: str = "harmonized"


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/meta")
def meta(request: Request) -> dict:
    store = request.app.state.store
    return {
        "data_origin": store.meta.get("data_origin"),
        "origin_note_es": store.meta.get("origin_note_es"),
        "date_min": store.meta.get("date_min"),
        "date_max": store.meta.get("date_max"),
        "year_min": store.meta.get("year_min"),
        "year_max": store.meta.get("year_max"),
        "partial_years": store.meta.get("partial_years"),
        "grid_degrees": store.meta.get("grid_degrees", GRID_DEGREES),
        "transition_year": store.meta.get("transition_year", TRANSITION_YEAR),
        "kept": store.meta.get("kept"),
        "dropped_low_confidence": store.meta.get("dropped_low_confidence"),
        "dropped_invalid": store.meta.get("dropped_invalid"),
        "by_sensor": store.meta.get("by_sensor"),
        "assumptions_es": store.meta.get("assumptions_es", ASSUMPTIONS_ES),
        "regions": REGIONS,
        "use_cases": USE_CASES,
    }


@router.get("/query")
def query_get(
    request: Request,
    region: str | None = None,
    bbox: str | None = None,
    year: int = 2022,
    month: int = Query(7, ge=1, le=12),
    sensor: str = Query("harmonized", pattern="^(harmonized|modis|viirs)$"),
) -> dict:
    parsed_bbox = _parse_bbox(bbox) if bbox else None
    return _run(request, region, parsed_bbox, None, year, month, sensor)


@router.post("/query")
def query_post(body: QueryBody, request: Request) -> dict:
    return _run(request, body.region_id, body.bbox, body.polygon, body.year, body.month, body.sensor)


def _parse_bbox(text: str) -> list[float]:
    parts = [piece.strip() for piece in text.split(",")]
    if len(parts) != 4:
        raise HTTPException(status_code=400, detail="El bbox es oeste,sur,este,norte.")
    try:
        return [float(piece) for piece in parts]
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="El bbox tiene que ser numérico.") from exc


def _run(
    request: Request,
    region_id: str | None,
    bbox: list[float] | None,
    polygon: list[list[float]] | None,
    year: int,
    month: int,
    sensor: str,
) -> dict:
    store = request.app.state.store
    try:
        area = resolve_area(region_id, bbox, polygon)
        return build_view(store.frame, store.meta, area, year, month, sensor)
    except QueryError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
