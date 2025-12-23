from __future__ import annotations

import pandas as pd


def detect_gaps(times: pd.Series, factor: float) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    if times.empty:
        return []
    times = times.reset_index(drop=True)
    deltas = times.diff().dropna()
    if deltas.empty:
        return []
    median = deltas.median()
    if pd.isna(median) or median <= pd.Timedelta(0):
        return []

    threshold = median * factor
    gaps: list[tuple[pd.Timestamp, pd.Timestamp]] = []
    for idx, delta in deltas.items():
        if delta > threshold:
            start = times.loc[idx - 1]
            end = times.loc[idx]
            gaps.append((start, end))
    return gaps
