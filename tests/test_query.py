import pandas as pd

from brasa.pipeline.harmonize import select_sensor
from brasa.services.query import build_view, filter_frame, resolve_area


def detections(rows: list[dict]) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    frame["acq_date"] = pd.to_datetime(frame["acq_date"])
    frame["year"] = frame["acq_date"].dt.year.astype(int)
    frame["month"] = frame["acq_date"].dt.month.astype(int)
    frame["satellite"] = frame.get("satellite", "N")
    frame["daynight"] = frame.get("daynight", "D")
    return frame


def meta(year_min=2012, year_max=2022) -> dict:
    return {
        "year_min": year_min,
        "year_max": year_max,
        "partial_years": [2026],
        "transition_year": 2012,
        "origin_note_es": "nota",
    }


def test_viirs_wins_from_2012_and_modis_stays_comparable():
    frame = detections(
        [
            {"lat": 40.0, "lon": -3.0, "acq_date": "2011-07-15", "sensor": "modis", "frp": 20, "satellite": "T", "daynight": "D"},
            {"lat": 40.0, "lon": -3.0, "acq_date": "2011-07-15", "sensor": "viirs", "frp": 999, "satellite": "N", "daynight": "D"},
            {"lat": 40.0, "lon": -3.0, "acq_date": "2022-07-15", "sensor": "modis", "frp": 5000, "satellite": "A", "daynight": "D"},
            {"lat": 40.0, "lon": -3.0, "acq_date": "2022-07-15", "sensor": "viirs", "frp": 40, "satellite": "N", "daynight": "N"},
        ]
    )
    area = resolve_area("spain")
    historical = select_sensor(filter_frame(frame, area), "harmonized")
    assert set(historical.loc[historical["year"] == 2011, "sensor"]) == {"modis"}
    assert float(historical.loc[historical["year"] == 2011, "frp"].sum()) == 20
    overlap = historical.loc[historical["year"] == 2022]
    assert set(overlap["sensor"]) == {"viirs"}
    assert float(overlap["frp"].sum()) == 40

    view = build_view(frame, meta(2011, 2022), area, 2022, 7, "modis")
    assert view["summary"]["active"]["frp"] == 5000
    heatmap = build_view(frame, meta(2011, 2022), area, 2011, 7, "harmonized")["heatmap"]
    assert {feature["properties"]["sensor"] for feature in heatmap["features"]} == {"modis"}


def test_polygon_keeps_only_interior_points():
    frame = detections(
        [
            {"lat": 0.0, "lon": 0.0, "acq_date": "2020-01-02", "sensor": "viirs", "frp": 5, "satellite": "N", "daynight": "D"},
            {"lat": 10.0, "lon": 10.0, "acq_date": "2020-01-02", "sensor": "viirs", "frp": 9, "satellite": "N", "daynight": "D"},
        ]
    )
    area = resolve_area(polygon=[[-1, -1], [1, -1], [1, 1], [-1, 1]])
    kept = filter_frame(frame, area)
    assert len(kept) == 1
    assert float(kept.iloc[0]["frp"]) == 5


def test_critical_month_uses_same_sensor_era_and_ignores_the_query_year():
    rows = []
    for year in range(2012, 2023):
        for month in range(1, 13):
            frp = 200 if year == 2022 and month == 7 else 10
            rows.append(
                {
                    "lat": 40.2,
                    "lon": -3.5,
                    "acq_date": f"{year}-{month:02d}-15",
                    "sensor": "viirs",
                    "frp": frp,
                    "satellite": "N",
                    "daynight": "D",
                }
            )
    rows.append(
        {
            "lat": 40.2,
            "lon": -3.5,
            "acq_date": "2022-07-16",
            "sensor": "modis",
            "frp": 9000,
            "satellite": "A",
            "daynight": "D",
        }
    )
    view = build_view(detections(rows), meta(), resolve_area("spain"), 2022, 7, "harmonized")
    assert view["critical_months"] == [7]
    july = next(item for item in view["months"] if item["month"] == 7)
    assert july["harmonized_frp"] == 200
    assert july["modis_frp"] == 9000
    assert len(view["calendar"]["days"]) == 365
    assert view["calendar"]["days"][195]["frp"] == 200  # 15 July is day 196, index 195


def test_partial_year_is_not_flagged():
    rows = []
    for year in range(2012, 2023):
        rows.append(
            {
                "lat": 40.2,
                "lon": -3.5,
                "acq_date": f"{year}-07-15",
                "sensor": "viirs",
                "frp": 10,
                "satellite": "N20",
                "daynight": "D",
            }
        )
    rows.append(
        {
            "lat": 40.2,
            "lon": -3.5,
            "acq_date": "2026-07-15",
            "sensor": "viirs",
            "frp": 500,
            "satellite": "N21",
            "daynight": "N",
        }
    )
    catalog = meta(2012, 2026)
    view = build_view(detections(rows), catalog, resolve_area("spain"), 2026, 7, "harmonized")
    assert view["critical_months"] == []
    assert view["partial_year"] is True
    assert view["satellites"][0]["name"] == "NOAA-21"
