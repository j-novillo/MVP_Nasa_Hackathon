"""Optional FIRMS area download. The app does not need this to start.

NASA FIRMS uses a free MAP_KEY, not the Earthdata DEMO_KEY. If the variable
is missing, or it is the literal DEMO_KEY and the request fails, the sample
CSVs remain the dataset.
"""

from __future__ import annotations

from pathlib import Path

import httpx

from brasa.config import FIRMS_AREA_URL, FIRMS_MAX_DAYS
from brasa.regions import REGIONS

SOURCES = (
    "MODIS_NRT",
    "VIIRS_SNPP_NRT",
    "VIIRS_NOAA20_NRT",
    "VIIRS_NOAA21_NRT",
)


def classify_key(key: str | None) -> str:
    if key is None or not str(key).strip():
        return "missing"
    if str(key).strip().upper() == "DEMO_KEY":
        return "demo"
    return "provided"


def looks_like_hotspot_csv(text: str) -> bool:
    if not text or not text.strip():
        return False
    header = text.lstrip().splitlines()[0].lower()
    return header.startswith("latitude,")


def exit_code(status: str, wrote_any: bool) -> int:
    if status == "missing" or status == "demo" or wrote_any:
        return 0
    return 1


def fetch_regions(
    key: str,
    dest: Path,
    days: int = 1,
    client: httpx.Client | None = None,
) -> list[Path]:
    """Download recent NRT CSVs into dest. Returns the files that parsed."""
    day_range = min(max(int(days), 1), FIRMS_MAX_DAYS)
    dest.mkdir(parents=True, exist_ok=True)
    own_client = client is None
    http = client or httpx.Client(timeout=90.0, follow_redirects=True)
    written: list[Path] = []
    try:
        for region in REGIONS:
            west, south, east, north = region["bbox"]
            bbox = f"{west},{south},{east},{north}"
            for source in SOURCES:
                url = FIRMS_AREA_URL.format(key=key.strip(), source=source, bbox=bbox, days=day_range)
                response = http.get(url)
                if response.status_code != 200 or not looks_like_hotspot_csv(response.text):
                    continue
                path = dest / f"firms_{source}_{region['id']}.csv"
                path.write_text(response.text, encoding="utf-8")
                written.append(path)
    finally:
        if own_client:
            http.close()
    if written:
        keep = {path.resolve() for path in written}
        for stale in dest.glob("firms_*.csv"):
            if stale.resolve() not in keep:
                stale.unlink()
        (dest / "ORIGIN").write_text("firms_api\n", encoding="utf-8")
    return written
