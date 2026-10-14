"""Sensor rule for the harmonized series.

From the hackathon MVP: during the overlap, VIIRS wins and MODIS stays
available as a comparative layer. There is no spatiotemporal clustering
and no cross-sensor FRP scaling.
"""

from __future__ import annotations

import pandas as pd

from brasa.config import TRANSITION_YEAR

SENSOR_MODES = ("harmonized", "modis", "viirs")


def harmonized_mask(frame: pd.DataFrame, transition_year: int = TRANSITION_YEAR) -> pd.Series:
    modis_history = (frame["sensor"] == "modis") & (frame["year"] < transition_year)
    viirs_era = (frame["sensor"] == "viirs") & (frame["year"] >= transition_year)
    return modis_history | viirs_era


def select_sensor(
    frame: pd.DataFrame,
    mode: str,
    transition_year: int = TRANSITION_YEAR,
) -> pd.DataFrame:
    if mode not in SENSOR_MODES:
        raise ValueError(f"Unknown sensor mode: {mode}")
    if frame.empty:
        return frame
    if mode == "modis":
        return frame.loc[frame["sensor"] == "modis"].copy()
    if mode == "viirs":
        return frame.loc[frame["sensor"] == "viirs"].copy()
    return frame.loc[harmonized_mask(frame, transition_year)].copy()
