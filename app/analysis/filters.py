from __future__ import annotations

import math
import pandas as pd
import numpy as np


def _has_alpha(text: str) -> bool:
    return any(ch.isalpha() for ch in text)


def _parse_sma_window(window) -> tuple[str, int | pd.Timedelta] | None:
    if window is None:
        return None
    if isinstance(window, str):
        text = window.strip()
        if not text:
            return None
        if not _has_alpha(text):
            value = int(float(text))
            if value <= 0:
                return None
            return ("samples", value)
        try:
            return ("time", pd.to_timedelta(text))
        except ValueError as exc:
            raise ValueError(
                "Invalid moving average window. Use samples (e.g., 10) or a time like 30min."
            ) from exc
    if isinstance(window, (int, float)):
        value = int(window)
        if value <= 0:
            return None
        return ("samples", value)
    raise ValueError("Invalid moving average window type.")


def _parse_ema_tau(tau) -> float | None:
    if tau is None:
        return None
    if isinstance(tau, str):
        text = tau.strip()
        if not text:
            return None
        if not _has_alpha(text):
            return float(text)
        try:
            return float(pd.to_timedelta(text).total_seconds())
        except ValueError as exc:
            raise ValueError(
                "Invalid exponential smoothing time. Use seconds (e.g., 60) or a time like 15min."
            ) from exc
    return float(tau)


def sma(series: pd.Series, window) -> pd.Series:
    parsed = _parse_sma_window(window)
    if parsed is None:
        return series
    mode, value = parsed
    if mode == "time":
        if not isinstance(series.index, pd.DatetimeIndex):
            raise ValueError("Time-based moving average requires timestamps.")
        return series.rolling(window=value, min_periods=1).mean()
    return series.rolling(window=int(value), min_periods=1).mean()


def ema_time_aware(series: pd.Series, tau, nan_mode: str = "skip") -> pd.Series:
    tau_seconds = _parse_ema_tau(tau)
    if tau_seconds is None:
        return series

    if tau_seconds <= 0:
        return series

    if not isinstance(series.index, pd.DatetimeIndex):
        series = series.copy()
        series.index = pd.to_datetime(series.index, unit="s", errors="coerce")

    values = series.values
    times = series.index
    out = np.full_like(values, fill_value=np.nan, dtype=float)

    prev = np.nan
    prev_time = None
    for i, value in enumerate(values):
        if pd.isna(value):
            if nan_mode == "reset":
                prev = np.nan
            elif nan_mode == "hold" and not pd.isna(prev):
                out[i] = prev
            continue
        if prev_time is None or pd.isna(prev):
            prev = float(value)
            out[i] = prev
            prev_time = times[i]
            continue

        dt = (times[i] - prev_time).total_seconds()
        if dt < 0:
            dt = 0
        alpha = 1.0 - math.exp(-dt / tau_seconds)
        prev = alpha * float(value) + (1 - alpha) * prev
        out[i] = prev
        prev_time = times[i]

    return pd.Series(out, index=series.index, name=series.name)
