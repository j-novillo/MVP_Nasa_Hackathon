"""Find local CSV inputs and map FIRMS columns onto one schema."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pandas as pd

from brasa.config import MODIS_LOW_CONFIDENCE_BELOW

SENSOR_MODIS = "modis"
SENSOR_VIIRS = "viirs"


def discover_inputs(data_dir: Path, include_samples: bool = False) -> tuple[list[Path], str]:
    """Prefer data/raw when it has CSVs. Otherwise use the bundled sample.

    A FIRMS fetch writes data/raw/ORIGIN containing ``firms_api``. Any other
    local drop is labeled ``local_csv``. Samples are not mixed in unless
    ``include_samples`` is set, so a one-day download does not sit on top of
    twenty synthetic years.
    """
    raw_dir = data_dir / "raw"
    sample_dir = data_dir / "samples"
    raw = sorted(p for p in raw_dir.glob("*.csv") if p.is_file()) if raw_dir.exists() else []
    samples = (
        sorted(p for p in sample_dir.glob("*.csv") if p.is_file()) if sample_dir.exists() else []
    )
    if raw:
        origin = "local_csv"
        marker = raw_dir / "ORIGIN"
        if marker.is_file() and marker.read_text(encoding="utf-8").strip() == "firms_api":
            origin = "firms_api"
        paths = raw + samples if include_samples else raw
        return paths, origin if not include_samples else "mixed"
    return samples, "synthetic_demo"


def file_signature(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return {"name": path.name, "bytes": path.stat().st_size, "sha256": digest.hexdigest()}


def input_signature(paths: list[Path]) -> list[dict]:
    return [file_signature(path) for path in paths]


def detect_sensor(columns: set[str], filename: str) -> str:
    if "bright_ti4" in columns or "bright_ti5" in columns:
        return SENSOR_VIIRS
    lowered = filename.lower()
    if "viirs" in lowered:
        return SENSOR_VIIRS
    return SENSOR_MODIS


def read_csv(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path, encoding="utf-8-sig")
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    return frame


def _series(frame: pd.DataFrame, *names: str) -> pd.Series:
    for name in names:
        if name in frame.columns:
            return frame[name]
    return pd.Series([pd.NA] * len(frame), index=frame.index)


def normalize_frame(frame: pd.DataFrame, sensor: str, source_file: str) -> pd.DataFrame:
    """Return one row per input detection with parsed fields and a drop reason."""
    brightness = _series(frame, "brightness", "bright_ti4")
    out = pd.DataFrame(
        {
            "lat": pd.to_numeric(_series(frame, "latitude", "lat"), errors="coerce"),
            "lon": pd.to_numeric(_series(frame, "longitude", "lon", "long"), errors="coerce"),
            "acq_date": pd.to_datetime(_series(frame, "acq_date", "date"), errors="coerce"),
            "acq_time_raw": _series(frame, "acq_time", "time").astype("string"),
            "satellite": _series(frame, "satellite").astype("string").str.strip().str.upper(),
            "confidence_raw": _series(frame, "confidence").astype("string").str.strip(),
            "frp": pd.to_numeric(_series(frame, "frp"), errors="coerce"),
            "daynight": _series(frame, "daynight").astype("string").str.strip().str.upper(),
            "brightness": pd.to_numeric(brightness, errors="coerce"),
            "version": _series(frame, "version").astype("string"),
            "sensor": sensor,
            "source_file": source_file,
        }
    )
    out["hour"] = out["acq_time_raw"].map(_parse_hour)
    out["confidence_class"] = [
        classify_confidence(sensor, value) for value in out["confidence_raw"]
    ]
    out["drop_reason"] = [
        _drop_reason(row) for row in out.itertuples(index=False)
    ]
    return out


def classify_confidence(sensor: str, value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "unknown"
    text = str(value).strip().lower()
    if text in {"", "<na>", "nan", "none"}:
        return "unknown"
    if text in {"low", "l"}:
        return "low"
    if text in {"nominal", "n", "medium"}:
        return "nominal"
    if text in {"high", "h"}:
        return "high"
    try:
        number = float(text)
    except ValueError:
        return "unknown"
    # Numeric scores use the FIRMS MODIS bins (low below 30, nominal below 80).
    if number < MODIS_LOW_CONFIDENCE_BELOW:
        return "low"
    if number < 80:
        return "nominal"
    return "high"


def _parse_hour(value: object) -> float:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return float("nan")
    text = str(value).strip()
    if text.endswith(".0"):
        text = text[:-2]
    if not text.isdigit():
        return float("nan")
    number = int(text)
    hour, minute = divmod(number, 100)
    if hour > 23 or minute > 59:
        return float("nan")
    return float(hour)


def _drop_reason(row: object) -> str:
    lat = row.lat
    lon = row.lon
    if pd.isna(lat) or pd.isna(lon) or not (-90 <= float(lat) <= 90 and -180 <= float(lon) <= 180):
        return "invalid"
    if pd.isna(row.acq_date):
        return "invalid"
    if pd.isna(row.frp) or float(row.frp) < 0:
        return "invalid"
    if row.confidence_class == "low":
        return "low_confidence"
    if row.confidence_class == "unknown":
        return "invalid"
    return ""
