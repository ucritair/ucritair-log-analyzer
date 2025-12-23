from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import pandas as pd


@dataclass
class Dataset:
    name: str
    raw: pd.DataFrame
    clean: pd.DataFrame
    masks: dict[str, pd.Series]
    flags: dict[str, pd.Series]
    metadata: dict[str, Any]
    resampled: pd.DataFrame | None = None
