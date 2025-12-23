from __future__ import annotations

from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class FlatlineConfig:
    min_samples: int = 5
    min_minutes: float = 10.0
    multi_channel_threshold: int = 3


def _flatline_mask(series: pd.Series, min_samples: int, min_minutes: float) -> pd.Series:
    if series.empty:
        return series.astype(bool)

    mask = pd.Series(False, index=series.index)
    values = series.values
    times = series.index

    run_start = 0
    for i in range(1, len(values) + 1):
        is_end = i == len(values)
        if not is_end and (pd.isna(values[i]) or pd.isna(values[i - 1]) or values[i] != values[i - 1]):
            run_end = i
        elif is_end:
            run_end = i
        else:
            continue

        if run_end - run_start >= 1:
            duration = times[run_end - 1] - times[run_start]
            if (run_end - run_start) >= min_samples or duration >= pd.Timedelta(minutes=min_minutes):
                mask.iloc[run_start:run_end] = True
        run_start = run_end

    return mask


def flag_flatlines(df: pd.DataFrame, cfg: FlatlineConfig) -> dict[str, pd.Series]:
    flags: dict[str, pd.Series] = {}
    if df.empty:
        return flags

    for col in df.columns:
        if col == "timestamp":
            continue
        series = df[col]
        if not isinstance(series.index, pd.DatetimeIndex):
            series = series.copy()
            series.index = pd.RangeIndex(len(series))
        flags[col] = _flatline_mask(series, cfg.min_samples, cfg.min_minutes)

    # Multi-channel diagnostic across particulate channels.
    pm_pn_cols = [c for c in df.columns if c.startswith("pm") or c.startswith("pn")]
    if pm_pn_cols:
        combined = pd.concat([flags[c] for c in pm_pn_cols if c in flags], axis=1)
        flags["multi_channel_flatline"] = combined.sum(axis=1) >= cfg.multi_channel_threshold

    return flags
