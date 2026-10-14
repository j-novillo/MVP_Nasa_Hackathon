#!/usr/bin/env python3
"""Write deterministic FIRMS-shaped CSVs for the three demo regions.

The files use the public MODIS C6.1 and VIIRS 375 m column layout so the
same parser accepts them and a real archive download. They are not NASA
observations. Seed and forced peaks are fixed so the prepared use cases
(Spain 2022, California 2020, Australia January 2020) stay visible.
"""

from __future__ import annotations

import csv
import json
import math
import random
import sys
from calendar import monthrange
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brasa.regions import get_region  # noqa: E402

SEED = 20261014
END = date(2026, 9, 30)

SEASONS = {
    "iberian_summer": {
        1: 0.12, 2: 0.16, 3: 0.32, 4: 0.48, 5: 0.75, 6: 1.25,
        7: 2.4, 8: 2.5, 9: 1.15, 10: 0.5, 11: 0.22, 12: 0.14,
    },
    "california_fall": {
        1: 0.12, 2: 0.12, 3: 0.18, 4: 0.28, 5: 0.45, 6: 0.85,
        7: 1.45, 8: 2.3, 9: 2.7, 10: 2.15, 11: 0.9, 12: 0.25,
    },
    "se_australia": {
        1: 2.5, 2: 2.1, 3: 1.05, 4: 0.4, 5: 0.22, 6: 0.16,
        7: 0.16, 8: 0.22, 9: 0.4, 10: 0.75, 11: 1.35, 12: 2.35,
    },
    "north_australia": {
        1: 0.28, 2: 0.22, 3: 0.28, 4: 0.55, 5: 1.35, 6: 2.15,
        7: 2.45, 8: 2.3, 9: 1.7, 10: 1.15, 11: 0.48, 12: 0.3,
    },
}

# Extra events on top of the seasonal background, only inside peak months.
FORCED = {
    ("spain", 2022, 7): 36,
    ("spain", 2022, 8): 28,
    ("california", 2020, 8): 22,
    ("california", 2020, 9): 34,
    ("california", 2020, 10): 18,
    ("australia", 2019, 12): 26,
    ("australia", 2020, 1): 34,
    ("australia", 2020, 2): 18,
}

REGIONS = [
    {
        "id": "spain",
        "year_boost": {2003: 1.7, 2005: 1.35, 2012: 1.45, 2017: 1.6, 2022: 1.15},
        "hotspots": [
            {"lat": 42.55, "lon": -8.15, "weight": 1.35, "season": "iberian_summer"},
            {"lat": 43.15, "lon": -7.05, "weight": 0.9, "season": "iberian_summer"},
            {"lat": 39.45, "lon": -0.55, "weight": 1.15, "season": "iberian_summer"},
            {"lat": 41.75, "lon": 1.55, "weight": 0.95, "season": "iberian_summer"},
            {"lat": 37.55, "lon": -6.35, "weight": 1.25, "season": "iberian_summer"},
            {"lat": 36.85, "lon": -3.55, "weight": 0.8, "season": "iberian_summer"},
            {"lat": 40.15, "lon": -5.85, "weight": 0.7, "season": "iberian_summer"},
        ],
    },
    {
        "id": "california",
        "year_boost": {2007: 1.45, 2008: 1.35, 2017: 1.55, 2018: 1.9, 2020: 1.2, 2021: 1.45},
        "hotspots": [
            {"lat": 40.7, "lon": -123.4, "weight": 1.3, "season": "california_fall"},
            {"lat": 39.4, "lon": -121.4, "weight": 0.85, "season": "california_fall"},
            {"lat": 37.75, "lon": -119.75, "weight": 1.25, "season": "california_fall"},
            {"lat": 36.15, "lon": -121.4, "weight": 0.7, "season": "california_fall"},
            {"lat": 34.25, "lon": -118.35, "weight": 1.05, "season": "california_fall"},
            {"lat": 33.05, "lon": -116.7, "weight": 0.75, "season": "california_fall"},
        ],
    },
    {
        "id": "australia",
        "year_boost": {2003: 1.25, 2009: 1.45, 2019: 1.35, 2020: 1.25},
        "hotspots": [
            {"lat": -33.6, "lon": 149.6, "weight": 1.3, "season": "se_australia"},
            {"lat": -37.1, "lon": 146.6, "weight": 1.2, "season": "se_australia"},
            {"lat": -35.0, "lon": 138.7, "weight": 0.55, "season": "se_australia"},
            {"lat": -33.4, "lon": 116.2, "weight": 0.7, "season": "se_australia"},
            {"lat": -15.5, "lon": 132.6, "weight": 1.35, "season": "north_australia"},
            {"lat": -17.9, "lon": 145.2, "weight": 1.0, "season": "north_australia"},
            {"lat": -24.8, "lon": 149.4, "weight": 0.65, "season": "se_australia"},
        ],
    },
]

MODIS_FIELDS = [
    "latitude", "longitude", "brightness", "scan", "track", "acq_date", "acq_time",
    "satellite", "confidence", "version", "bright_t31", "frp", "daynight",
]
VIIRS_FIELDS = [
    "latitude", "longitude", "bright_ti4", "scan", "track", "acq_date", "acq_time",
    "satellite", "confidence", "version", "bright_ti5", "frp", "daynight",
]


def poisson(rng: random.Random, lam: float) -> int:
    if lam <= 0:
        return 0
    limit = math.exp(-lam)
    count = 0
    product = 1.0
    while product > limit:
        count += 1
        product *= rng.random()
    return count - 1


def clamp(lat: float, lon: float, bbox: list[float]) -> tuple[float, float]:
    west, south, east, north = bbox
    return (
        min(max(lat, south + 0.05), north - 0.05),
        min(max(lon, west + 0.05), east - 0.05),
    )


def jitter(rng: random.Random, lat: float, lon: float, sigma: float, bbox: list[float]) -> tuple[float, float]:
    u1 = max(rng.random(), 1e-9)
    u2 = rng.random()
    lat2 = lat + sigma * math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)
    u3 = max(rng.random(), 1e-9)
    u4 = rng.random()
    lon2 = lon + sigma * math.sqrt(-2 * math.log(u3)) * math.cos(2 * math.pi * u4)
    return clamp(lat2, lon2, bbox)


def choose(rng: random.Random, hotspots: list[dict]) -> dict:
    total = sum(item["weight"] for item in hotspots)
    pick = rng.random() * total
    running = 0.0
    for item in hotspots:
        running += item["weight"]
        if pick <= running:
            return item
    return hotspots[-1]


def acq_time(hour: int, rng: random.Random) -> tuple[str, str]:
    minute = rng.randint(0, 49)
    flag = "D" if 6 <= hour <= 18 else "N"
    return f"{hour:02d}{minute:02d}", flag


def log_frp(rng: random.Random, median: float, sigma: float, low: float, high: float, scale: float) -> float:
    value = rng.lognormvariate(math.log(median), sigma) * scale
    return round(min(max(value, low), high), 2)


def emit_modis(rows: list[dict], rng: random.Random, lat: float, lon: float, when: date, bbox, scale: float) -> None:
    satellites = ["T"]
    if when.year >= 2002:
        satellites.append("A")
    nominal = {"T": 10, "A": 13}
    night = {"T": 22, "A": 1}
    for satellite in satellites:
        if rng.random() < 0.1:
            continue
        point_lat, point_lon = jitter(rng, lat, lon, 0.18, bbox)
        clock, flag = acq_time(nominal[satellite], rng)
        frp = log_frp(rng, 28, 0.55, 1.0, 650, scale)
        low = rng.random() < 0.18
        confidence = rng.randint(0, 29) if low else rng.randint(30, 100)
        brightness = round(305 + min(frp, 180) * 0.35 + rng.uniform(-4, 4), 2)
        rows.append(
            {
                "latitude": round(point_lat, 5),
                "longitude": round(point_lon, 5),
                "brightness": brightness,
                "scan": round(rng.uniform(1.0, 2.4), 2),
                "track": round(rng.uniform(1.0, 1.6), 2),
                "acq_date": when.isoformat(),
                "acq_time": clock,
                "satellite": satellite,
                "confidence": confidence,
                "version": "6.1",
                "bright_t31": round(rng.uniform(282, 296), 2),
                "frp": frp,
                "daynight": flag,
            }
        )
        if rng.random() < 0.22:
            night_lat, night_lon = jitter(rng, lat, lon, 0.18, bbox)
            clock, flag = acq_time(night[satellite], rng)
            night_frp = log_frp(rng, 18, 0.5, 1.0, 400, scale)
            low = rng.random() < 0.18
            rows.append(
                {
                    "latitude": round(night_lat, 5),
                    "longitude": round(night_lon, 5),
                    "brightness": round(300 + min(night_frp, 160) * 0.3, 2),
                    "scan": round(rng.uniform(1.0, 2.2), 2),
                    "track": round(rng.uniform(1.0, 1.5), 2),
                    "acq_date": when.isoformat(),
                    "acq_time": clock,
                    "satellite": satellite,
                    "confidence": rng.randint(0, 29) if low else rng.randint(30, 100),
                    "version": "6.1",
                    "bright_t31": round(rng.uniform(280, 292), 2),
                    "frp": night_frp,
                    "daynight": flag,
                }
            )


def viirs_satellites(year: int) -> list[str]:
    satellites = ["N"]
    if year >= 2018:
        satellites.append("N20")
    if year >= 2023:
        satellites.append("N21")
    return satellites


def emit_viirs(rows: list[dict], rng: random.Random, lat: float, lon: float, when: date, bbox, scale: float) -> None:
    for satellite in viirs_satellites(when.year):
        bursts = 2 if rng.random() < 0.65 else 1
        for _ in range(bursts):
            if rng.random() < 0.08:
                continue
            point_lat, point_lon = jitter(rng, lat, lon, 0.12, bbox)
            clock, flag = acq_time(13, rng)
            frp = log_frp(rng, 6.5, 0.85, 0.4, 420, scale)
            if rng.random() < 0.2:
                confidence = "low"
            elif rng.random() < 0.35:
                confidence = "high"
            else:
                confidence = "nominal"
            rows.append(
                {
                    "latitude": round(point_lat, 5),
                    "longitude": round(point_lon, 5),
                    "bright_ti4": round(300 + min(frp, 120) * 0.55 + rng.uniform(-3, 3), 2),
                    "scan": round(rng.uniform(0.38, 0.75), 2),
                    "track": round(rng.uniform(0.36, 0.62), 2),
                    "acq_date": when.isoformat(),
                    "acq_time": clock,
                    "satellite": satellite,
                    "confidence": confidence,
                    "version": "2.0",
                    "bright_ti5": round(rng.uniform(284, 298), 2),
                    "frp": frp,
                    "daynight": flag,
                }
            )


def peak_hotspots(hotspots: list[dict], month: int) -> list[dict]:
    chosen = [item for item in hotspots if SEASONS[item["season"]][month] >= 1]
    return chosen or hotspots


def add_events(
    modis_rows: list[dict],
    viirs_rows: list[dict],
    rng: random.Random,
    hotspots: list[dict],
    bbox: list[float],
    when: date,
    count: int,
    scale: float,
) -> None:
    for _ in range(count):
        spot = choose(rng, hotspots)
        lat, lon = jitter(rng, spot["lat"], spot["lon"], 0.35, bbox)
        emit_modis(modis_rows, rng, lat, lon, when, bbox, scale)
        if when.year >= 2012:
            emit_viirs(viirs_rows, rng, lat, lon, when, bbox, scale * 0.85)


def generate(rng: random.Random) -> tuple[list[dict], list[dict]]:
    modis_rows: list[dict] = []
    viirs_rows: list[dict] = []
    for region in REGIONS:
        bbox = get_region(region["id"])["bbox"]
        hotspots = region["hotspots"]
        year = 2000
        while date(year, 1, 1) <= END:
            for month in range(1, 13):
                if date(year, month, 1) > END:
                    break
                for spot in hotspots:
                    season = SEASONS[spot["season"]][month]
                    boost = region["year_boost"].get(year, 1.0) if season >= 1 else 1.0
                    lam = season * spot["weight"] * boost * rng.uniform(0.85, 1.15) * 0.42
                    events = poisson(rng, lam)
                    for _ in range(events):
                        day = rng.randint(1, monthrange(year, month)[1])
                        when = date(year, month, day)
                        lat, lon = jitter(rng, spot["lat"], spot["lon"], 0.42, bbox)
                        emit_modis(modis_rows, rng, lat, lon, when, bbox, 1.0)
                        if year >= 2012:
                            emit_viirs(viirs_rows, rng, lat, lon, when, bbox, 0.9)
                extra = FORCED.get((region["id"], year, month), 0)
                if extra:
                    targets = peak_hotspots(hotspots, month)
                    for _ in range(extra):
                        day = rng.randint(1, monthrange(year, month)[1])
                        add_events(
                            modis_rows,
                            viirs_rows,
                            rng,
                            targets,
                            bbox,
                            date(year, month, day),
                            1,
                            2.4,
                        )
            year += 1
    return modis_rows, viirs_rows


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def month_frp(rows: list[dict], bbox: list[float], month: int) -> dict[int, float]:
    west, south, east, north = bbox
    totals: dict[int, float] = {}
    for row in rows:
        if int(row["acq_date"][5:7]) != month:
            continue
        lat = float(row["latitude"])
        lon = float(row["longitude"])
        if not (south <= lat <= north and west <= lon <= east):
            continue
        if isinstance(row["confidence"], str) and row["confidence"] == "low":
            continue
        if isinstance(row["confidence"], int) and row["confidence"] < 30:
            continue
        year = int(row["acq_date"][0:4])
        totals[year] = totals.get(year, 0.0) + float(row["frp"])
    return totals


def main() -> None:
    rng = random.Random(SEED)
    modis_rows, viirs_rows = generate(rng)
    out = ROOT / "data" / "samples"
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "modis_demo.csv", MODIS_FIELDS, modis_rows)
    write_csv(out / "viirs_demo.csv", VIIRS_FIELDS, viirs_rows)
    spain = get_region("spain")["bbox"]
    california = get_region("california")["bbox"]
    australia = get_region("australia")["bbox"]
    summary = {
        "seed": SEED,
        "synthetic": True,
        "modis_rows": len(modis_rows),
        "viirs_rows": len(viirs_rows),
        "spain_july_viirs_frp": {str(k): round(v, 1) for k, v in sorted(month_frp(viirs_rows, spain, 7).items())},
        "california_september_viirs_frp": {
            str(k): round(v, 1) for k, v in sorted(month_frp(viirs_rows, california, 9).items())
        },
        "australia_january_viirs_frp": {
            str(k): round(v, 1) for k, v in sorted(month_frp(viirs_rows, australia, 1).items())
        },
    }
    (out / "manifest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
