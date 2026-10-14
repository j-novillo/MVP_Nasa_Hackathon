#!/usr/bin/env bash
# Create a virtualenv if needed, install pinned deps, and start Brasa.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
if ! python -c "import fastapi, pandas, httpx" >/dev/null 2>&1; then
  pip install -r requirements.txt
fi
exec python -m brasa
