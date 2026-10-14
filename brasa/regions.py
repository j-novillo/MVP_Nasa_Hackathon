"""Preset areas and prepared hackathon use cases.

Bounding boxes are [west, south, east, north] in degrees.
"""

from __future__ import annotations

REGIONS = [
    {
        "id": "spain",
        "name": "España (península)",
        "bbox": [-9.5, 35.9, 3.4, 43.9],
        "center": [40.2, -3.7],
        "zoom": 6,
        "blurb": (
            "Península ibérica, sin Canarias. En la muestra, los fuegos de verano "
            "se concentran en el noroeste, el suroeste y el litoral mediterráneo."
        ),
    },
    {
        "id": "california",
        "name": "California",
        "bbox": [-124.5, 32.5, -114.1, 42.1],
        "center": [37.3, -119.5],
        "zoom": 6,
        "blurb": (
            "Costa oeste de Estados Unidos. La muestra imita el pico de finales "
            "de verano y otoño, con temporadas duras en 2018 y 2020."
        ),
    },
    {
        "id": "australia",
        "name": "Australia",
        "bbox": [112.0, -44.0, 154.0, -10.0],
        "center": [-25.8, 134.0],
        "zoom": 4,
        "blurb": (
            "El continente entero. El sureste quema en el verano austral y el "
            "norte en la estación seca; el área dibujada cambia el calendario."
        ),
    },
]

USE_CASES = [
    {
        "id": "spain-summer-2022",
        "name": "Verano 2022 en España",
        "region_id": "spain",
        "year": 2022,
        "month": 7,
        "sensor": "harmonized",
        "blurb": (
            "Caso preparado: julio de 2022 en la península. En la muestra el FRP "
            "de ese verano queda por encima de la climatología VIIRS."
        ),
    },
    {
        "id": "california-2020",
        "name": "Otoño 2020 en California",
        "region_id": "california",
        "year": 2020,
        "month": 9,
        "sensor": "harmonized",
        "blurb": (
            "Caso preparado: septiembre de 2020. Sirve para ver un pico de "
            "finales de verano en la era VIIRS."
        ),
    },
    {
        "id": "australia-black-summer",
        "name": "Enero 2020 en Australia",
        "region_id": "australia",
        "year": 2020,
        "month": 1,
        "sensor": "harmonized",
        "blurb": (
            "Caso preparado del verano austral 2019-2020. Enero concentra el "
            "pico del sureste en la muestra; el norte sigue su propia estación."
        ),
    },
]


def get_region(region_id: str) -> dict | None:
    for region in REGIONS:
        if region["id"] == region_id:
            return region
    return None


def get_use_case(use_case_id: str) -> dict | None:
    for case in USE_CASES:
        if case["id"] == use_case_id:
            return case
    return None
