#!/usr/bin/env python3
"""Download a short FIRMS NRT window when FIRMS_MAP_KEY is set.

Without a key, or when DEMO_KEY is rejected, this exits successfully and
leaves the bundled sample in place. A real key that fails exits with status 1.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from brasa.config import DATA_DIR, FIRMS_MAX_DAYS  # noqa: E402
from brasa.pipeline.fetch import classify_key, exit_code, fetch_regions  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch recent FIRMS active-fire CSVs")
    parser.add_argument("--days", type=int, default=1, help=f"1 to {FIRMS_MAX_DAYS} days")
    parser.add_argument("--out", type=Path, default=DATA_DIR / "raw")
    args = parser.parse_args()
    key = os.environ.get("FIRMS_MAP_KEY", "")
    status = classify_key(key)
    if status == "missing":
        print("FIRMS_MAP_KEY is unset. Using the bundled sample CSVs. Nothing was downloaded.")
        return exit_code(status, False)
    try:
        written = fetch_regions(key, args.out, args.days)
    except Exception as exc:  # network, DNS, timeout
        print(f"FIRMS request failed ({exc}).")
        written = []
    if written:
        print(f"Wrote {len(written)} file(s) to {args.out}.")
        print("Rebuild with: python -m brasa.pipeline.build")
        print("data/raw replaces the synthetic sample on the next build. Delete those CSVs to restore it.")
        return exit_code(status, True)
    if status == "demo":
        print("DEMO_KEY was not accepted by FIRMS. The sample dataset stays in place.")
        return exit_code(status, False)
    print("FIRMS_MAP_KEY was set but no CSV was downloaded. Check the key, the bbox, and the day range.")
    return exit_code(status, False)


if __name__ == "__main__":
    raise SystemExit(main())
