from pathlib import Path

import pandas as pd

from brasa.pipeline.build import build_dataset
from brasa.pipeline.clean import clean_paths
from brasa.pipeline.grid import monthly_aggregate, snap_edge
from brasa.pipeline.ingest import classify_confidence

FIXTURES = Path(__file__).parent / "fixtures"


def test_confidence_bins():
    assert classify_confidence("modis", "29") == "low"
    assert classify_confidence("modis", 30) == "nominal"
    assert classify_confidence("modis", "80") == "high"
    assert classify_confidence("viirs", "low") == "low"
    assert classify_confidence("viirs", "Nominal") == "nominal"
    assert classify_confidence("viirs", "h") == "high"


def test_real_firms_headers_drop_low_confidence():
    kept, stats = clean_paths(
        [FIXTURES / "modis_snippet.csv", FIXTURES / "viirs_snippet.csv"]
    )
    assert stats["input_rows"] == 5
    assert stats["dropped_low_confidence"] == 2
    assert stats["dropped_invalid"] == 1
    assert stats["kept"] == 2
    sensors = set(kept["sensor"])
    assert sensors == {"modis", "viirs"}
    modis = kept.loc[kept["sensor"] == "modis"].iloc[0]
    assert modis["frp"] == 22.38
    assert int(modis["hour"]) == 0
    assert modis["satellite"] == "T"
    viirs = kept.loc[kept["sensor"] == "viirs"].iloc[0]
    assert viirs["confidence_class"] == "nominal"
    assert viirs["frp"] == 1.92


def test_grid_edges_including_southern_hemisphere():
    edges = [float(value) for value in snap_edge(pd.Series([40.0, 40.25, 40.249, -33.0, -33.0001]))]
    assert edges == [40.0, 40.25, 40.0, -33.0, -33.25]


def test_monthly_aggregate_sums_frp(tmp_path: Path):
    frame = pd.DataFrame(
        {
            "lat": [40.1, 40.2, -33.2],
            "lon": [-3.1, -3.2, 149.2],
            "frp": [10.0, 5.5, 3.0],
            "sensor": ["modis", "modis", "viirs"],
            "year": [2010, 2010, 2020],
            "month": [7, 7, 1],
        }
    )
    grid = monthly_aggregate(frame)
    spain = grid.loc[grid["sensor"] == "modis"].iloc[0]
    assert spain["count"] == 2
    assert spain["frp_sum"] == 15.5
    assert bool(spain["in_harmonized_series"]) is True
    australia = grid.loc[grid["sensor"] == "viirs"].iloc[0]
    assert bool(australia["in_harmonized_series"]) is True
    meta = build_dataset_from_frame(tmp_path, frame)
    assert meta["kept"] == 3
    assert (tmp_path / "processed" / "monthly_grid.geojson").is_file()


def build_dataset_from_frame(tmp_path: Path, frame: pd.DataFrame) -> dict:
    raw = tmp_path / "raw"
    raw.mkdir()
    out = frame.copy()
    out["acq_date"] = [
        f"{year}-{month:02d}-15" for year, month in zip(out["year"], out["month"], strict=True)
    ]
    out["acq_time"] = "1200"
    out["satellite"] = "T"
    out["confidence"] = 90
    out["bright_t31"] = 290
    out["brightness"] = 320
    out["scan"] = 1
    out["track"] = 1
    out["version"] = "6.1"
    out["daynight"] = "D"
    modis = out.loc[out["sensor"] == "modis"].rename(columns={"lat": "latitude", "lon": "longitude"})
    viirs = out.loc[out["sensor"] == "viirs"].rename(
        columns={"lat": "latitude", "lon": "longitude", "brightness": "bright_ti4"}
    )
    if len(modis):
        modis.to_csv(raw / "modis.csv", index=False)
    if len(viirs):
        viirs["confidence"] = "nominal"
        viirs["bright_ti5"] = 290
        viirs.to_csv(raw / "viirs.csv", index=False)
    return __import__("brasa.pipeline.build", fromlist=["build_dataset"]).build_dataset(tmp_path)
