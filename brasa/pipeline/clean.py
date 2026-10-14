"""Drop low-confidence and unusable hotspot rows."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from brasa.pipeline.ingest import detect_sensor, normalize_frame, read_csv

KEPT_COLUMNS = [
    "lat",
    "lon",
    "acq_date",
    "hour",
    "satellite",
    "sensor",
    "confidence",
    "confidence_class",
    "frp",
    "daynight",
    "brightness",
    "version",
    "source_file",
]


def clean_paths(paths: list[Path]) -> tuple[pd.DataFrame, dict]:
    stats = {
        "input_rows": 0,
        "kept": 0,
        "dropped_low_confidence": 0,
        "dropped_invalid": 0,
        "files": [],
        "by_sensor": {"modis": 0, "viirs": 0},
    }
    kept_frames: list[pd.DataFrame] = []
    for path in paths:
        frame = read_csv(path)
        sensor = detect_sensor(set(frame.columns), path.name)
        normalized = normalize_frame(frame, sensor, path.name)
        reasons = normalized["drop_reason"]
        kept_mask = reasons == ""
        low = int((reasons == "low_confidence").sum())
        invalid = int((reasons == "invalid").sum())
        kept_n = int(kept_mask.sum())
        stats["input_rows"] += int(len(normalized))
        stats["dropped_low_confidence"] += low
        stats["dropped_invalid"] += invalid
        stats["kept"] += kept_n
        stats["files"].append(
            {
                "name": path.name,
                "sensor_guess": sensor,
                "input_rows": int(len(normalized)),
                "kept": kept_n,
                "dropped_low_confidence": low,
                "dropped_invalid": invalid,
            }
        )
        if kept_n:
            kept_frames.append(normalized.loc[kept_mask])

    if not kept_frames:
        empty = pd.DataFrame(columns=KEPT_COLUMNS + ["year", "month"])
        return empty, stats

    kept = pd.concat(kept_frames, ignore_index=True)
    kept["acq_date"] = pd.to_datetime(kept["acq_date"])
    kept["year"] = kept["acq_date"].dt.year.astype(int)
    kept["month"] = kept["acq_date"].dt.month.astype(int)
    kept["confidence"] = kept["confidence_raw"].astype("string")
    kept["frp"] = kept["frp"].astype(float).round(2)
    kept["lat"] = kept["lat"].astype(float).round(5)
    kept["lon"] = kept["lon"].astype(float).round(5)
    for sensor, count in kept["sensor"].value_counts().items():
        stats["by_sensor"][str(sensor)] = int(count)
    ordered = kept[KEPT_COLUMNS + ["year", "month"]].sort_values(
        ["acq_date", "sensor", "lat", "lon"]
    )
    return ordered.reset_index(drop=True), stats
