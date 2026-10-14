"""Paths, harmonization constants, and optional FIRMS credentials."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT / "frontend"
# Bump when processed meta should be rebuilt even if the CSV bytes did not change.
PIPELINE_VERSION = 2


def load_env_file(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from .env without overriding the real environment."""
    env_path = path or (ROOT / ".env")
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

DATA_DIR = Path(os.environ.get("BRASA_DATA_DIR", ROOT / "data"))

# Monthly grid from the hackathon proposal (option A/B), not a radiometric calibration.
GRID_DEGREES = 0.25
# VIIRS 375 m record used for the harmonized series from this calendar year onward.
TRANSITION_YEAR = 2012
# FIRMS MODIS confidence classes: low 0–29, nominal 30–79, high 80–100.
MODIS_LOW_CONFIDENCE_BELOW = 30
# Sample archive is complete through September 2026; that year is not a baseline.
PARTIAL_YEARS = (2026,)
# Minimum baseline years before a month can be called critical.
MIN_BASELINE_YEARS = 3
CRITICAL_SIGMA = 1.5

FIRMS_AREA_URL = (
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{bbox}/{days}"
)
FIRMS_MAX_DAYS = 5

ASSUMPTIONS_ES = [
    "La serie armonizada usa MODIS antes de 2012 y VIIRS desde 2012, inclusive.",
    "MODIS posterior a 2012 se conserva solo como capa comparativa, no se suma a VIIRS.",
    "No hay calibración radiométrica ni un factor de conversión de FRP entre sensores.",
    "No se deduplican detecciones cercanas: Terra, Aqua y los distintos VIIRS pueden contar el mismo fuego.",
    "No se normaliza por órbitas ni por píxeles observados. Más satélites pueden inflar los conteos.",
    "Se descartan las detecciones de confianza baja: MODIS por debajo de 30 y VIIRS etiquetado low.",
    "La métrica es la suma de FRP en megavatios, no la energía integrada ni el área quemada.",
    "La agregación de referencia es mensual en celdas de 0,25°. El calendario diario usa la misma regla de sensor.",
    "Un mes crítico supera en 1,5 desviaciones típicas la media de ese mes en la misma era de sensor, sin el año consultado, y además concentra al menos un 25% del FRP del mes más alto de ese año.",
    "No se corrige el ciclo diurno: Terra observa por la mañana y Aqua/VIIRS por la tarde.",
]

SATELLITES = {
    "T": {"name": "Terra", "sensor": "MODIS", "pass_es": "Mañana ~10:30, órbita descendente"},
    "A": {"name": "Aqua", "sensor": "MODIS", "pass_es": "Tarde ~13:30, órbita ascendente"},
    "N": {"name": "S-NPP", "sensor": "VIIRS", "pass_es": "Tarde ~13:30"},
    "N20": {"name": "NOAA-20", "sensor": "VIIRS", "pass_es": "Tarde ~13:30"},
    "N21": {"name": "NOAA-21", "sensor": "VIIRS", "pass_es": "Tarde ~13:30"},
}
