"""Filter an area of interest and build calendar, series, and heatmap."""

from __future__ import annotations

import calendar
from datetime import date

import numpy as np
import pandas as pd

from brasa.config import (
    CRITICAL_SIGMA,
    GRID_DEGREES,
    MIN_BASELINE_YEARS,
    PARTIAL_YEARS,
    SATELLITES,
    TRANSITION_YEAR,
)
from brasa.pipeline.grid import cell_ring, snap_edge
from brasa.pipeline.harmonize import SENSOR_MODES, select_sensor
from brasa.regions import get_region


class QueryError(ValueError):
    """The area or the parameters cannot be queried."""


def resolve_area(
    region_id: str | None = None,
    bbox: list[float] | None = None,
    polygon: list[list[float]] | None = None,
) -> dict:
    if polygon is not None:
        if len(polygon) < 3 or len(polygon) > 200:
            raise QueryError("El polígono necesita entre 3 y 200 vértices.")
        ring = []
        for point in polygon:
            if len(point) != 2:
                raise QueryError("Cada vértice del polígono es [longitud, latitud].")
            lon, lat = float(point[0]), float(point[1])
            _check_coord(lat, lon)
            ring.append([lon, lat])
        lons = [point[0] for point in ring]
        lats = [point[1] for point in ring]
        return {
            "kind": "polygon",
            "label": "Área dibujada",
            "region_id": None,
            "polygon": ring,
            "bbox": [min(lons), min(lats), max(lons), max(lats)],
        }
    if bbox is not None:
        if len(bbox) != 4:
            raise QueryError("El bbox es [oeste, sur, este, norte].")
        west, south, east, north = (float(v) for v in bbox)
        _check_coord(south, west)
        _check_coord(north, east)
        if west >= east or south >= north:
            raise QueryError("El bbox está vacío: el oeste debe ser menor que el este y el sur menor que el norte.")
        return {
            "kind": "bbox",
            "label": "Rectángulo",
            "region_id": None,
            "polygon": None,
            "bbox": [west, south, east, north],
        }
    if region_id:
        region = get_region(region_id)
        if region is None:
            raise QueryError(f"Región desconocida: {region_id}")
        return {
            "kind": "region",
            "label": region["name"],
            "region_id": region_id,
            "polygon": None,
            "bbox": list(region["bbox"]),
        }
    raise QueryError("Indica una región, un bbox o un polígono.")


def _check_coord(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise QueryError("Coordenadas fuera de rango.")


def filter_frame(frame: pd.DataFrame, area: dict) -> pd.DataFrame:
    if frame.empty:
        return frame
    west, south, east, north = area["bbox"]
    boxed = frame[
        (frame["lon"] >= west)
        & (frame["lon"] <= east)
        & (frame["lat"] >= south)
        & (frame["lat"] <= north)
    ]
    polygon = area.get("polygon")
    if not polygon:
        return boxed
    if boxed.empty:
        return boxed
    mask = points_in_polygon(boxed["lon"].to_numpy(), boxed["lat"].to_numpy(), polygon)
    return boxed.iloc[np.flatnonzero(mask)]


def points_in_polygon(lon: np.ndarray, lat: np.ndarray, polygon: list[list[float]]) -> np.ndarray:
    """Ray casting. Polygon vertices are [lon, lat]."""
    x = np.asarray(lon, dtype=float)
    y = np.asarray(lat, dtype=float)
    inside = np.zeros(len(x), dtype=bool)
    if len(polygon) < 3:
        return inside
    xs = [point[0] for point in polygon]
    ys = [point[1] for point in polygon]
    if xs[0] != xs[-1] or ys[0] != ys[-1]:
        xs.append(xs[0])
        ys.append(ys[0])
    for i in range(len(xs) - 1):
        x1, y1 = xs[i], ys[i]
        x2, y2 = xs[i + 1], ys[i + 1]
        if y1 == y2:
            continue
        crosses = ((y1 > y) != (y2 > y)) & (x < (x2 - x1) * (y - y1) / (y2 - y1) + x1)
        inside ^= crosses
    return inside


def build_view(
    frame: pd.DataFrame,
    meta: dict,
    area: dict,
    year: int,
    month: int,
    sensor: str,
) -> dict:
    if sensor not in SENSOR_MODES:
        raise QueryError("El sensor debe ser harmonized, modis o viirs.")
    if month < 1 or month > 12:
        raise QueryError("El mes tiene que estar entre 1 y 12.")
    if year < 1980 or year > 2100:
        raise QueryError("Año fuera de rango.")

    inside = filter_frame(frame, area)
    active = select_sensor(inside, sensor)
    year_min = int(meta["year_min"]) if meta.get("year_min") is not None else year
    year_max = int(meta["year_max"]) if meta.get("year_max") is not None else year
    partial = set(meta.get("partial_years") or PARTIAL_YEARS)
    transition = int(meta.get("transition_year") or TRANSITION_YEAR)

    months = _month_flags(inside, sensor, year, transition, partial, year_min, year_max)
    return {
        "area": area,
        "year": year,
        "month": month,
        "sensor": sensor,
        "transition_year": transition,
        "partial_year": year in partial,
        "summary": _summary(inside, active, sensor, year, month),
        "satellites": _satellites(active.loc[active["year"] == year] if len(active) else active),
        "calendar": _calendar(active, year),
        "months": months,
        "annual": _annual(inside, year_min, year_max),
        "heatmap": _heatmap(active, year, month),
        "critical_months": [row["month"] for row in months if row["critical"]],
        "notes_es": _notes(sensor, year, transition, bool(year in partial), meta),
    }


def _summary(inside: pd.DataFrame, active: pd.DataFrame, sensor: str, year: int, month: int) -> dict:
    """Headline totals follow the selected year. The map is the selected month."""

    def pack(subset: pd.DataFrame) -> dict:
        if subset is None or len(subset) == 0:
            return {"count": 0, "frp": 0.0}
        return {"count": int(len(subset)), "frp": round(float(subset["frp"].sum()), 2)}

    def in_year(subset: pd.DataFrame) -> pd.DataFrame:
        if len(subset) == 0:
            return subset
        return subset.loc[subset["year"] == year]

    active_year = in_year(active)
    active_month = active_year.loc[active_year["month"] == month] if len(active_year) else active_year
    if len(inside) == 0:
        modis_year = inside
        viirs_year = inside
    else:
        modis_year = in_year(inside.loc[inside["sensor"] == "modis"])
        viirs_year = in_year(inside.loc[inside["sensor"] == "viirs"])
    return {
        "year": year,
        "month": month,
        "detections_in_area": int(len(inside)),
        "by_sensor": {"modis": pack(modis_year), "viirs": pack(viirs_year)},
        "active": {**pack(active_year), "sensor": sensor},
        "active_month": {**pack(active_month), "sensor": sensor},
    }


def _satellites(year_frame: pd.DataFrame) -> list[dict]:
    if year_frame.empty or "satellite" not in year_frame.columns:
        return []
    counts = year_frame["satellite"].fillna("").astype(str).str.upper().value_counts()
    rows = []
    for code, count in counts.items():
        if not code or code == "<NA>":
            continue
        info = SATELLITES.get(code, {"name": code, "sensor": "", "pass_es": "Hora local no documentada"})
        day = int((year_frame.loc[year_frame["satellite"].astype(str).str.upper() == code, "daynight"] == "D").sum())
        night = int((year_frame.loc[year_frame["satellite"].astype(str).str.upper() == code, "daynight"] == "N").sum())
        rows.append(
            {
                "code": code,
                "name": info["name"],
                "sensor": info["sensor"],
                "pass_es": info["pass_es"],
                "count": int(count),
                "day": day,
                "night": night,
            }
        )
    return rows


def _calendar(active: pd.DataFrame, year: int) -> dict:
    days_in_year = 366 if calendar.isleap(year) else 365
    start = date(year, 1, 1)
    frp = np.zeros(days_in_year, dtype=float)
    counts = np.zeros(days_in_year, dtype=int)
    if len(active):
        subset = active.loc[active["year"] == year]
        if len(subset):
            day_index = (subset["acq_date"].dt.dayofyear - 1).to_numpy()
            for index, value in zip(day_index, subset["frp"].to_numpy(), strict=True):
                if 0 <= int(index) < days_in_year:
                    frp[int(index)] += float(value)
                    counts[int(index)] += 1
    level, thresholds = _levels(frp)
    days = []
    for offset in range(days_in_year):
        current = date.fromordinal(start.toordinal() + offset)
        days.append(
            {
                "date": current.isoformat(),
                "count": int(counts[offset]),
                "frp": round(float(frp[offset]), 2),
                "level": int(level[offset]),
            }
        )
    return {
        "year": year,
        "week_starts": "monday",
        "metric": "frp",
        "thresholds_frp": [round(v, 2) for v in thresholds],
        "days": days,
    }


def _levels(frp: np.ndarray) -> tuple[np.ndarray, list[float]]:
    positive = np.sort(frp[frp > 0])
    levels = np.zeros(len(frp), dtype=int)
    if len(positive) == 0:
        return levels, [0.0, 0.0, 0.0]
    quantiles = [float(np.quantile(positive, q)) for q in (0.25, 0.5, 0.75)]
    levels[frp > 0] = 1
    levels[frp > quantiles[0]] = 2
    levels[frp > quantiles[1]] = 3
    levels[frp > quantiles[2]] = 4
    levels[frp <= 0] = 0
    return levels, quantiles


def _month_flags(
    inside: pd.DataFrame,
    sensor: str,
    year: int,
    transition: int,
    partial: set[int],
    year_min: int,
    year_max: int,
) -> list[dict]:
    by_mode = {mode: _sum_by_year_month(select_sensor(inside, mode)) for mode in SENSOR_MODES}
    totals = by_mode[sensor]
    baseline_years = _baseline_years(sensor, year, transition, partial, year_min, year_max)
    year_peak = max(totals.get((year, month), 0.0) for month in range(1, 13))
    rows = []
    for month in range(1, 13):
        frp = totals.get((year, month), 0.0)
        count = int(totals.get((year, month, "count"), 0))
        critical = False
        mean = None
        stdev = None
        if year not in partial and len(baseline_years) >= MIN_BASELINE_YEARS:
            sample = [totals.get((y, month), 0.0) for y in baseline_years]
            mean = float(np.mean(sample))
            stdev = float(np.std(sample))
            # The share-of-peak cut ignores a near-zero month that only looks
            # extreme because other years of that month are also near zero.
            critical = (
                frp > 0
                and year_peak > 0
                and frp >= 0.25 * year_peak
                and frp > mean + CRITICAL_SIGMA * stdev
            )
        row = {
            "month": month,
            "frp": round(frp, 2),
            "count": count,
            "critical": critical,
            "baseline_mean_frp": None if mean is None else round(mean, 2),
            "baseline_stdev_frp": None if stdev is None else round(stdev, 2),
        }
        for mode in SENSOR_MODES:
            mode_totals = by_mode[mode]
            row[f"{mode}_frp"] = round(mode_totals.get((year, month), 0.0), 2)
            row[f"{mode}_count"] = int(mode_totals.get((year, month, "count"), 0))
        rows.append(row)
    return rows


def _sum_by_year_month(frame: pd.DataFrame) -> dict:
    totals: dict = {}
    if frame.empty:
        return totals
    grouped = frame.groupby(["year", "month"], as_index=False).agg(frp=("frp", "sum"), count=("frp", "size"))
    for row in grouped.itertuples(index=False):
        totals[(int(row.year), int(row.month))] = float(row.frp)
        totals[(int(row.year), int(row.month), "count")] = int(row.count)
    return totals


def _baseline_years(
    sensor: str,
    year: int,
    transition: int,
    partial: set[int],
    year_min: int,
    year_max: int,
) -> list[int]:
    if sensor == "viirs" or (sensor == "harmonized" and year >= transition):
        start = max(year_min, transition)
    elif sensor == "harmonized":
        start = year_min
        year_max = min(year_max, transition - 1)
    else:
        start = year_min
    return [y for y in range(start, year_max + 1) if y != year and y not in partial]


def _annual(inside: pd.DataFrame, year_min: int, year_max: int) -> list[dict]:
    rows = []
    if year_max < year_min:
        return rows
    for year in range(year_min, year_max + 1):
        chunk = inside.loc[inside["year"] == year] if len(inside) else inside
        modis = select_sensor(chunk, "modis") if len(chunk) else chunk
        viirs = select_sensor(chunk, "viirs") if len(chunk) else chunk
        harmonized = select_sensor(chunk, "harmonized") if len(chunk) else chunk

        def pack(subset: pd.DataFrame) -> tuple[int, float]:
            if subset is None or subset.empty:
                return 0, 0.0
            return int(len(subset)), round(float(subset["frp"].sum()), 2)

        modis_n, modis_frp = pack(modis)
        viirs_n, viirs_frp = pack(viirs)
        harm_n, harm_frp = pack(harmonized)
        rows.append(
            {
                "year": year,
                "modis_count": modis_n,
                "modis_frp": modis_frp,
                "viirs_count": viirs_n,
                "viirs_frp": viirs_frp,
                "harmonized_count": harm_n,
                "harmonized_frp": harm_frp,
            }
        )
    return rows


def _heatmap(active: pd.DataFrame, year: int, month: int) -> dict:
    subset = active.loc[(active["year"] == year) & (active["month"] == month)] if len(active) else active
    features = []
    if len(subset):
        work = subset.copy()
        work["cell_lat"] = snap_edge(work["lat"])
        work["cell_lon"] = snap_edge(work["lon"])
        grouped = work.groupby(["cell_lat", "cell_lon", "sensor"], as_index=False).agg(
            count=("frp", "size"), frp=("frp", "sum")
        )
        for row in grouped.itertuples(index=False):
            features.append(
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [cell_ring(row.cell_lat, row.cell_lon, GRID_DEGREES)],
                    },
                    "properties": {
                        "sensor": row.sensor,
                        "count": int(row.count),
                        "frp": round(float(row.frp), 2),
                        "cell_lat": float(row.cell_lat),
                        "cell_lon": float(row.cell_lon),
                    },
                }
            )
    return {"type": "FeatureCollection", "features": features}


def _notes(sensor: str, year: int, transition: int, partial: bool, meta: dict) -> list[str]:
    notes = []
    if sensor == "harmonized" and year >= transition:
        notes.append(
            f"En {year} la serie armonizada usa solo VIIRS. MODIS de ese año está en la capa comparativa."
        )
    elif sensor == "harmonized":
        notes.append(
            f"En {year} aún no entra VIIRS en la serie armonizada. Se usa MODIS, el registro histórico."
        )
    elif sensor == "viirs" and year < transition:
        notes.append("VIIRS 375 m no tiene archivo en este proyecto antes de 2012. El mapa puede salir vacío.")
    elif sensor == "modis" and year >= transition:
        notes.append("Estás viendo MODIS en el periodo de solape, no la serie armonizada.")
    if partial:
        notes.append("Este año está incompleto en los datos cargados y no se marca como crítico.")
    origin = meta.get("origin_note_es")
    if origin:
        notes.append(origin)
    return notes
