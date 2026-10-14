"""Snap detections to the 0.25° monthly grid and export it."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from brasa.config import GRID_DEGREES, TRANSITION_YEAR


def snap_edge(values: pd.Series | np.ndarray, grid: float = GRID_DEGREES) -> np.ndarray:
    """Southwest edge of the cell that contains each coordinate."""
    array = np.asarray(values, dtype=float)
    edges = np.floor(array / grid + 1e-9) * grid
    return np.round(edges, 4)


def assign_cells(frame: pd.DataFrame, grid: float = GRID_DEGREES) -> pd.DataFrame:
    out = frame.copy()
    out["cell_lat"] = snap_edge(out["lat"], grid)
    out["cell_lon"] = snap_edge(out["lon"], grid)
    return out


def monthly_aggregate(frame: pd.DataFrame, grid: float = GRID_DEGREES) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(
            columns=["sensor", "year", "month", "cell_lat", "cell_lon", "count", "frp_sum", "in_harmonized_series"]
        )
    placed = assign_cells(frame, grid)
    grouped = (
        placed.groupby(["sensor", "year", "month", "cell_lat", "cell_lon"], as_index=False)
        .agg(count=("frp", "size"), frp_sum=("frp", "sum"))
    )
    grouped["frp_sum"] = grouped["frp_sum"].round(2)
    grouped["in_harmonized_series"] = [
        (sensor == "modis" and int(year) < TRANSITION_YEAR)
        or (sensor == "viirs" and int(year) >= TRANSITION_YEAR)
        for sensor, year in zip(grouped["sensor"], grouped["year"], strict=True)
    ]
    return grouped.sort_values(["year", "month", "sensor", "cell_lat", "cell_lon"]).reset_index(drop=True)


def cell_ring(lat: float, lon: float, grid: float = GRID_DEGREES) -> list[list[float]]:
    lat_r = round(float(lat), 4)
    lon_r = round(float(lon), 4)
    lat_n = round(lat_r + grid, 4)
    lon_e = round(lon_r + grid, 4)
    return [
        [lon_r, lat_r],
        [lon_e, lat_r],
        [lon_e, lat_n],
        [lon_r, lat_n],
        [lon_r, lat_r],
    ]


def grid_to_geojson(grid_frame: pd.DataFrame, grid: float = GRID_DEGREES) -> dict:
    features = []
    for row in grid_frame.itertuples(index=False):
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [cell_ring(row.cell_lat, row.cell_lon, grid)]},
                "properties": {
                    "sensor": row.sensor,
                    "year": int(row.year),
                    "month": int(row.month),
                    "period": f"{int(row.year):04d}-{int(row.month):02d}",
                    "count": int(row.count),
                    "frp_sum": float(row.frp_sum),
                    "cell_lat": float(row.cell_lat),
                    "cell_lon": float(row.cell_lon),
                    "cell_degrees": grid,
                    "in_harmonized_series": bool(row.in_harmonized_series),
                },
            }
        )
    return {"type": "FeatureCollection", "features": features}


def write_grid(grid_frame: pd.DataFrame, processed_dir: Path, grid: float = GRID_DEGREES) -> None:
    processed_dir.mkdir(parents=True, exist_ok=True)
    grid_frame.to_csv(processed_dir / "monthly_grid.csv", index=False)
    payload = grid_to_geojson(grid_frame, grid)
    (processed_dir / "monthly_grid.geojson").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
