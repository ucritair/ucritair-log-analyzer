from __future__ import annotations

import pandas as pd
from app.core.config import FilterConfig
from app.analysis.filters import sma, ema_time_aware


def cache_filtered(df: pd.DataFrame, filters: FilterConfig) -> pd.DataFrame:
    out = df.copy()
    for col in df.columns:
        if col == "timestamp":
            continue
        series = df[col]
        if filters.sma_window is not None:
            series = sma(series, filters.sma_window)
        if filters.ema_tau is not None:
            series = ema_time_aware(series, filters.ema_tau, filters.ema_nan_mode)
        out[col] = series
    return out
