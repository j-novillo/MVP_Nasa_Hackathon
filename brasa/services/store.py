"""In-memory hotspot table loaded from the processed CSV."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from brasa.pipeline.build import load_processed


@dataclass
class DataStore:
    frame: pd.DataFrame
    meta: dict

    @classmethod
    def load_default(cls) -> "DataStore":
        frame, meta = load_processed()
        return cls(frame=frame, meta=meta)
