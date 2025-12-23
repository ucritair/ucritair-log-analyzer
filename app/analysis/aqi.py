from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import pandas as pd
import numpy as np
import yaml


@dataclass
class StandardPack:
    name: str
    breakpoints: dict[str, list[tuple[float, float, int, int]]]
    rounding: dict[str, str]
    categories: list[dict[str, Any]] | None = None
    concentration_truncation: dict[str, float] | None = None
    extrapolate_upper: bool | None = None


def load_standard_pack(path: Path) -> StandardPack:
    data = yaml.safe_load(path.read_text())
    return StandardPack(
        name=data["name"],
        breakpoints=data["breakpoints"],
        rounding=data.get("rounding", {}),
        categories=data.get("categories"),
        concentration_truncation=data.get("concentration_truncation"),
        extrapolate_upper=data.get("extrapolate_upper"),
    )


def _round_half_up(value: float) -> float:
    return float(np.floor(value + 0.5))


def _apply_rounding(value: float, mode: str) -> float:
    if mode == "round":
        return _round_half_up(value)
    if mode == "floor":
        return float(int(value))
    if mode == "truncate":
        return float(int(value))
    return value


def _compute_subindex(
    series: pd.Series,
    breakpoints,
    rounding_mode: str,
    extrapolate_upper: bool = False,
) -> pd.Series:
    result = pd.Series(index=series.index, dtype=float)
    ordered = sorted(breakpoints, key=lambda row: row[0])
    for idx, (conc_low, conc_high, idx_low, idx_high) in enumerate(ordered):
        if extrapolate_upper and idx == len(ordered) - 1:
            mask = series >= conc_low
        else:
            mask = (series >= conc_low) & (series <= conc_high)
        if not mask.any():
            continue
        sub = (idx_high - idx_low) / (conc_high - conc_low) * (series[mask] - conc_low) + idx_low
        result.loc[mask] = sub.apply(lambda v: _apply_rounding(float(v), rounding_mode))
    return result


def _truncate_series(series: pd.Series, step: float) -> pd.Series:
    if step <= 0:
        return series
    values = series.to_numpy(dtype=float)
    scale = 1.0 / step
    truncated = np.floor(values * scale + 1e-9) / scale
    return pd.Series(truncated, index=series.index, name=series.name)


def _lookup_truncation(trunc_map: dict[str, float] | None, *keys: str) -> float | None:
    if not trunc_map:
        return None
    for key in keys:
        if key in trunc_map:
            return trunc_map[key]
    return None


def apply_averaging(series: pd.Series, mode: str) -> pd.Series:
    if mode == "instant":
        return series
    if not isinstance(series.index, pd.DatetimeIndex):
        raise ValueError("Averaging requires DatetimeIndex")
    if mode == "rolling_24h":
        return series.rolling("24h", min_periods=1).mean()
    if mode == "daily":
        return series.resample("D").mean()
    return series


def compute_aqi(pm25: pd.Series | None, pm10: pd.Series | None, pack: StandardPack) -> pd.DataFrame:
    data: dict[str, pd.Series] = {}
    pm25_key = "pm2_5" if "pm2_5" in pack.breakpoints else "pm25"
    trunc_map = pack.concentration_truncation or {}
    if pm25 is not None and pm25_key in pack.breakpoints:
        step = _lookup_truncation(trunc_map, pm25_key, "pm25", "pm2_5")
        series = _truncate_series(pm25, step) if step else pm25
        rounding_mode = (
            pack.rounding.get(pm25_key)
            or pack.rounding.get("pm25")
            or pack.rounding.get("pm2_5")
            or "round"
        )
        data["aqi_pm25"] = _compute_subindex(
            series,
            pack.breakpoints[pm25_key],
            rounding_mode,
            extrapolate_upper=bool(pack.extrapolate_upper),
        )
    if pm10 is not None and "pm10" in pack.breakpoints:
        step = _lookup_truncation(trunc_map, "pm10")
        series = _truncate_series(pm10, step) if step else pm10
        data["aqi_pm10"] = _compute_subindex(
            series,
            pack.breakpoints["pm10"],
            pack.rounding.get("pm10", "round"),
            extrapolate_upper=bool(pack.extrapolate_upper),
        )

    df = pd.DataFrame(data)
    if not df.empty:
        df["aqi_overall"] = df.max(axis=1, skipna=True)
        if pack.categories:
            df["aqi_category"] = classify_aqi(df["aqi_overall"], pack.categories)
    return df


def classify_aqi(aqi_series: pd.Series, categories: list[dict[str, Any]]) -> pd.Series:
    out = pd.Series(index=aqi_series.index, dtype=object)
    for cat in categories:
        low = cat["low"]
        high = cat["high"]
        name = cat["name"]
        mask = (aqi_series >= low) & (aqi_series <= high)
        out.loc[mask] = name
    return out


def aqi_summary(aqi_series: pd.Series, categories: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    summary["max"] = float(aqi_series.max()) if not aqi_series.empty else None
    summary["mean"] = float(aqi_series.mean()) if not aqi_series.empty else None

    if categories and isinstance(aqi_series.index, pd.DatetimeIndex):
        deltas = aqi_series.index.to_series().diff().dt.total_seconds().fillna(0)
        for cat in categories:
            low = cat["low"]
            high = cat["high"]
            name = cat["name"]
            mask = (aqi_series >= low) & (aqi_series <= high)
            seconds = float(deltas[mask].sum())
            summary[f"time_{name}"] = seconds
    return summary
