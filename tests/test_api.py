import pandas as pd
from fastapi.testclient import TestClient

from brasa.main import create_app
from brasa.services.store import DataStore


def sample_store() -> DataStore:
    frame = pd.DataFrame(
        {
            "lat": [40.4, 40.4, 37.5],
            "lon": [-3.7, -3.7, -119.5],
            "acq_date": pd.to_datetime(["2010-07-02", "2022-07-18", "2020-09-05"]),
            "hour": [10, 13, 13],
            "satellite": ["T", "N", "N20"],
            "sensor": ["modis", "viirs", "viirs"],
            "confidence": ["80", "nominal", "high"],
            "confidence_class": ["high", "nominal", "high"],
            "frp": [12.0, 30.0, 50.0],
            "daynight": ["D", "D", "D"],
            "brightness": [320.0, 330.0, 340.0],
            "version": ["6.1", "2.0", "2.0"],
            "source_file": ["modis_demo.csv", "viirs_demo.csv", "viirs_demo.csv"],
        }
    )
    frame["year"] = frame["acq_date"].dt.year.astype(int)
    frame["month"] = frame["acq_date"].dt.month.astype(int)
    meta = {
        "data_origin": "synthetic_demo",
        "origin_note_es": "Muestra sintética.",
        "date_min": "2010-07-02",
        "date_max": "2022-07-18",
        "year_min": 2010,
        "year_max": 2022,
        "partial_years": [],
        "grid_degrees": 0.25,
        "transition_year": 2012,
        "kept": 3,
        "dropped_low_confidence": 1,
        "dropped_invalid": 0,
        "by_sensor": {"modis": 1, "viirs": 2},
        "assumptions_es": ["VIIRS desde 2012."],
    }
    return DataStore(frame=frame, meta=meta)


def test_health_meta_and_region_query():
    client = TestClient(create_app(sample_store()))
    assert client.get("/api/health").json()["status"] == "ok"
    meta = client.get("/api/meta").json()
    assert meta["data_origin"] == "synthetic_demo"
    assert any(region["id"] == "spain" for region in meta["regions"])
    spain = client.get("/api/query", params={"region": "spain", "year": 2022, "month": 7, "sensor": "harmonized"})
    assert spain.status_code == 200
    body = spain.json()
    assert body["summary"]["active"]["frp"] == 30
    assert body["heatmap"]["features"]
    assert body["heatmap"]["features"][0]["properties"]["sensor"] == "viirs"
    historical = client.get("/api/query", params={"region": "spain", "year": 2010, "month": 7}).json()
    assert historical["heatmap"]["features"][0]["properties"]["sensor"] == "modis"
    unknown = client.get("/api/query", params={"region": "atlantis"})
    assert unknown.status_code == 400


def test_post_polygon_and_index():
    client = TestClient(create_app(sample_store()))
    response = client.post(
        "/api/query",
        json={
            "polygon": [[-4.2, 40.0], [-3.2, 40.0], [-3.2, 40.8], [-4.2, 40.8]],
            "year": 2022,
            "month": 7,
            "sensor": "harmonized",
        },
    )
    assert response.status_code == 200
    assert response.json()["summary"]["active"]["count"] == 1
    index = client.get("/")
    assert index.status_code == 200
    assert "Calendario" in index.text
