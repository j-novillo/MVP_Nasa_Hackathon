import httpx

from brasa.pipeline.fetch import classify_key, exit_code, fetch_regions, looks_like_hotspot_csv


def test_key_classification_and_exit_codes():
    assert classify_key(None) == "missing"
    assert classify_key("  ") == "missing"
    assert classify_key("DEMO_KEY") == "demo"
    assert classify_key("demo_key") == "demo"
    assert classify_key("map-key-123") == "provided"
    assert exit_code("missing", False) == 0
    assert exit_code("demo", False) == 0
    assert exit_code("provided", False) == 1
    assert exit_code("provided", True) == 0
    assert looks_like_hotspot_csv("latitude,longitude\n")
    assert not looks_like_hotspot_csv("<html>no</html>")


def test_fetch_writes_only_real_csv(tmp_path):
    def handler(request: httpx.Request) -> httpx.Response:
        if "VIIRS_NOAA21_NRT" in str(request.url):
            return httpx.Response(403, text="Invalid MAP_KEY")
        return httpx.Response(200, text="latitude,longitude,frp\n10,20,1\n")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    written = fetch_regions("DEMO_KEY", tmp_path, days=9, client=client)
    names = sorted(path.name for path in written)
    assert names
    assert all("NOAA21" not in name for name in names)
    assert (tmp_path / "ORIGIN").read_text(encoding="utf-8").strip() == "firms_api"
    assert all(path.read_text(encoding="utf-8").startswith("latitude,") for path in written)
