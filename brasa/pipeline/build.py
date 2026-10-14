"""Build the static files the API serves. No database."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from brasa.config import (
    ASSUMPTIONS_ES,
    DATA_DIR,
    GRID_DEGREES,
    MODIS_LOW_CONFIDENCE_BELOW,
    PARTIAL_YEARS,
    PIPELINE_VERSION,
    TRANSITION_YEAR,
)
from brasa.pipeline.clean import clean_paths
from brasa.pipeline.grid import monthly_aggregate, write_grid
from brasa.pipeline.ingest import discover_inputs, input_signature

ORIGIN_NOTES = {
    "synthetic_demo": (
        "Datos de demostración sintéticos con el esquema CSV de NASA FIRMS. "
        "No son observaciones reales. Sirven para recorrer el calendario; "
        "copia CSV de archivo en data/raw y reconstruye antes de una demo con datos reales."
    ),
    "firms_api": (
        "CSV descargados de la API de área de FIRMS (cerca de tiempo real, ventana de pocos días). "
        "No sustituyen el archivo histórico 2000-2026 salvo que añadas esos CSV en data/raw."
    ),
    "local_csv": (
        "Detecciones leídas de los CSV en data/raw. El calendario cubre solo el rango de fechas de esos ficheros."
    ),
    "mixed": (
        "Mezcla de data/raw y de la muestra sintética. Úsalo solo para pruebas: los conteos no son interpretables."
    ),
}


def build_dataset(data_dir: Path | None = None, include_samples: bool = False) -> dict:
    root = Path(data_dir) if data_dir is not None else DATA_DIR
    paths, origin = discover_inputs(root, include_samples=include_samples)
    kept, stats = clean_paths(paths)
    grid = monthly_aggregate(kept, GRID_DEGREES)
    processed = root / "processed"
    processed.mkdir(parents=True, exist_ok=True)

    export = kept.drop(columns=["year", "month"])
    export.to_csv(processed / "detections.csv", index=False)
    write_grid(grid, processed, GRID_DEGREES)

    if kept.empty:
        date_min = None
        date_max = None
        year_min = None
        year_max = None
    else:
        date_min = kept["acq_date"].min().date().isoformat()
        date_max = kept["acq_date"].max().date().isoformat()
        year_min = int(kept["year"].min())
        year_max = int(kept["year"].max())

    meta = {
        "product": "brasa",
        "pipeline_version": PIPELINE_VERSION,
        "data_origin": origin,
        "origin_note_es": ORIGIN_NOTES[origin],
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "grid_degrees": GRID_DEGREES,
        "transition_year": TRANSITION_YEAR,
        "modis_low_confidence_below": MODIS_LOW_CONFIDENCE_BELOW,
        "partial_years": list(PARTIAL_YEARS),
        "date_min": date_min,
        "date_max": date_max,
        "year_min": year_min,
        "year_max": year_max,
        "assumptions_es": ASSUMPTIONS_ES,
        "inputs": input_signature(paths),
        **stats,
    }
    (processed / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return meta


def processed_is_current(data_dir: Path | None = None) -> bool:
    root = Path(data_dir) if data_dir is not None else DATA_DIR
    meta_path = root / "processed" / "meta.json"
    detections = root / "processed" / "detections.csv"
    if not meta_path.is_file() or not detections.is_file():
        return False
    paths, origin = discover_inputs(root)
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return (
        meta.get("inputs") == input_signature(paths)
        and meta.get("data_origin") == origin
        and meta.get("pipeline_version") == PIPELINE_VERSION
    )


def load_processed(data_dir: Path | None = None) -> tuple[pd.DataFrame, dict]:
    root = Path(data_dir) if data_dir is not None else DATA_DIR
    if not processed_is_current(root):
        build_dataset(root)
    frame = pd.read_csv(root / "processed" / "detections.csv", parse_dates=["acq_date"])
    if frame.empty:
        frame = pd.DataFrame(
            columns=[
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
        )
        frame["acq_date"] = pd.to_datetime(frame["acq_date"])
    frame["year"] = frame["acq_date"].dt.year.astype(int) if len(frame) else pd.Series(dtype=int)
    frame["month"] = frame["acq_date"].dt.month.astype(int) if len(frame) else pd.Series(dtype=int)
    if len(frame):
        frame["year"] = frame["year"].astype(int)
        frame["month"] = frame["month"].astype(int)
    meta = json.loads((root / "processed" / "meta.json").read_text(encoding="utf-8"))
    return frame, meta


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Brasa static hotspot files")
    parser.add_argument("--data-dir", type=Path, default=None)
    parser.add_argument(
        "--include-samples",
        action="store_true",
        help="Mix data/samples into data/raw. Counts will not be interpretable.",
    )
    args = parser.parse_args()
    meta = build_dataset(args.data_dir, include_samples=args.include_samples)
    print(
        f"origin={meta['data_origin']} kept={meta['kept']} "
        f"dropped_low={meta['dropped_low_confidence']} dropped_invalid={meta['dropped_invalid']} "
        f"range={meta['date_min']}..{meta['date_max']}"
    )


if __name__ == "__main__":
    main()
