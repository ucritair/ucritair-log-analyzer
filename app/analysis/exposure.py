from __future__ import annotations

import pandas as pd
import numpy as np


def _as_time_seconds(series: pd.Series) -> tuple[pd.Series, np.ndarray]:
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Exposure requires DatetimeIndex")
    times = series.index
    dt = times.to_series().diff().dt.total_seconds().fillna(0).to_numpy()
    return series, dt


def exposure_auc(series: pd.Series) -> float:
    series, dt = _as_time_seconds(series)
    values = series.fillna(0).to_numpy(dtype=float)
    return float(np.sum(values * dt))


def exceedance_auc(series: pd.Series, threshold: float) -> float:
    series, dt = _as_time_seconds(series)
    values = np.maximum(series.fillna(0).to_numpy(dtype=float) - threshold, 0.0)
    return float(np.sum(values * dt))


def time_above(series: pd.Series, threshold: float) -> pd.Timedelta:
    series, dt = _as_time_seconds(series)
    mask = series > threshold
    seconds = np.sum(dt[mask.to_numpy(dtype=bool)])
    return pd.Timedelta(seconds=seconds)


def exposure_stats(series: pd.Series, threshold: float) -> dict[str, float]:
    series, dt = _as_time_seconds(series)
    values = series.fillna(0).to_numpy(dtype=float)
    total_seconds = float(np.sum(dt))
    auc = float(np.sum(values * dt))
    ex_values = np.maximum(values - threshold, 0.0)
    ex_auc = float(np.sum(ex_values * dt))
    above_seconds = float(np.sum(dt[values > threshold]))
    mean = auc / total_seconds if total_seconds > 0 else float("nan")
    mean_excess = ex_auc / total_seconds if total_seconds > 0 else float("nan")
    time_above_pct = (above_seconds / total_seconds * 100.0) if total_seconds > 0 else float("nan")
    relative = (mean / threshold) if threshold > 0 else float("nan")
    return {
        "auc": auc,
        "exceedance_auc": ex_auc,
        "time_above_seconds": above_seconds,
        "total_seconds": total_seconds,
        "mean": mean,
        "mean_excess": mean_excess,
        "time_above_pct": time_above_pct,
        "relative_to_threshold": relative,
    }


def summarize_periods(series: pd.Series, threshold: float, freq: str) -> pd.DataFrame:
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Exposure requires DatetimeIndex")

    df = pd.DataFrame({"value": series})
    grouped = df.resample(freq)

    rows = []
    for start, group in grouped:
        if group.empty:
            continue
        group_series = group["value"]
        stats = exposure_stats(group_series, threshold)
        end = group_series.index.max()
        rows.append(
            {
                "start": start,
                "end": end,
                "auc": stats["auc"],
                "exceedance_auc": stats["exceedance_auc"],
                "time_above_seconds": stats["time_above_seconds"],
                "mean": stats["mean"],
                "mean_excess": stats["mean_excess"],
                "time_above_pct": stats["time_above_pct"],
                "relative_to_threshold": stats["relative_to_threshold"],
                "total_seconds": stats["total_seconds"],
            }
        )

    return pd.DataFrame(rows)
