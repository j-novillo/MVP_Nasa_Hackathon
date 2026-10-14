"""Locks the prepared stories in the bundled synthetic archive."""

from fastapi.testclient import TestClient

from brasa.main import app

client = TestClient(app)


def test_catalog_is_the_synthetic_sample():
    meta = client.get("/api/meta").json()
    assert meta["data_origin"] == "synthetic_demo"
    assert meta["transition_year"] == 2012
    assert meta["grid_degrees"] == 0.25
    assert meta["dropped_low_confidence"] > 0
    assert meta["year_min"] <= 2000
    assert meta["year_max"] >= 2026
    assert {region["id"] for region in meta["regions"]} == {"spain", "california", "australia"}


def test_prepared_use_cases_flag_the_extreme_month():
    stories = [
        ("spain", 2022, 7, 1),
        ("california", 2020, 9, 2),
        ("australia", 2020, 1, 6),
    ]
    for region, year, month, quiet_month in stories:
        view = client.get(
            "/api/query",
            params={"region": region, "year": year, "month": month, "sensor": "harmonized"},
        ).json()
        assert month in view["critical_months"]
        assert quiet_month not in view["critical_months"]
        assert view["summary"]["active_month"]["frp"] > 0
        sensors = {feature["properties"]["sensor"] for feature in view["heatmap"]["features"]}
        assert sensors == {"viirs"}
        assert len(view["calendar"]["days"]) == (366 if year % 4 == 0 else 365)


def test_harmonized_heatmap_uses_modis_before_viirs_exists():
    view = client.get(
        "/api/query",
        params={"region": "spain", "year": 2010, "month": 7, "sensor": "harmonized"},
    ).json()
    sensors = {feature["properties"]["sensor"] for feature in view["heatmap"]["features"]}
    assert sensors == {"modis"}
    comparative = client.get(
        "/api/query",
        params={"region": "spain", "year": 2022, "month": 7, "sensor": "modis"},
    ).json()
    assert comparative["heatmap"]["features"]
    assert {feature["properties"]["sensor"] for feature in comparative["heatmap"]["features"]} == {"modis"}
    empty = client.get(
        "/api/query",
        params={"region": "spain", "year": 2010, "month": 7, "sensor": "viirs"},
    ).json()
    assert empty["heatmap"]["features"] == []
