from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
import numpy as np
import pandas as pd
from scipy.optimize import curve_fit


@dataclass
class DecayFitResult:
    k_per_hr: float
    ach: float
    baseline: float
    r2: float
    ci: tuple[float, float] | None
    warnings: list[str]
    residuals: pd.Series


@dataclass
class DecayEvent:
    label: str
    start: pd.Timestamp
    end: pd.Timestamp
    peak_time: pd.Timestamp
    peak_value: float
    baseline: float
    method: str
    ach: float
    r2: float
    warnings: list[str]


def _to_hours(times: pd.Series) -> np.ndarray:
    t0 = times.iloc[0]
    delta = (times - t0).dt.total_seconds() / 3600.0
    return delta.to_numpy()


def _r2(y, yhat) -> float:
    ss_res = np.nansum((y - yhat) ** 2)
    ss_tot = np.nansum((y - np.nanmean(y)) ** 2)
    if ss_tot == 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def fit_co2_decay(
    times: pd.Series,
    co2: pd.Series,
    baseline: float,
    method: Literal["regression", "two_point", "time_constant_63"] = "regression",
) -> DecayFitResult:
    warnings = []
    times = times.reset_index(drop=True)
    co2 = co2.reset_index(drop=True)

    if method == "time_constant_63":
        valid = (co2 > baseline)
        if valid.sum() < 2:
            warnings.append("Insufficient points above baseline")
            return DecayFitResult(0.0, 0.0, baseline, 0.0, None, warnings, pd.Series(dtype=float))
        c_excess = (co2 - baseline).to_numpy(dtype=float)
        if np.nanmax(c_excess) <= 0:
            warnings.append("No positive excess CO2 above baseline")
            return DecayFitResult(0.0, 0.0, baseline, 0.0, None, warnings, pd.Series(dtype=float))
        peak_idx = int(np.nanargmax(c_excess))
        peak_value = c_excess[peak_idx]
        target = peak_value / np.e
        cross_idx = None
        for i in range(peak_idx + 1, len(c_excess)):
            if np.isnan(c_excess[i]):
                continue
            if c_excess[i] <= target:
                cross_idx = i
                break
        if cross_idx is None:
            warnings.append("Did not reach 63% decay threshold")
            return DecayFitResult(0.0, 0.0, baseline, 0.0, None, warnings, pd.Series(dtype=float))

        # Linear interpolation between the two points around the threshold.
        t0 = times.iloc[cross_idx - 1]
        t1 = times.iloc[cross_idx]
        y0 = c_excess[cross_idx - 1]
        y1 = c_excess[cross_idx]
        if y1 == y0:
            t_cross = t1
        else:
            frac = (target - y0) / (y1 - y0)
            t_cross = t0 + (t1 - t0) * float(frac)

        t_peak = times.iloc[peak_idx]
        tau_hours = (t_cross - t_peak).total_seconds() / 3600.0
        if tau_hours <= 0:
            warnings.append("Invalid time constant")
            return DecayFitResult(0.0, 0.0, baseline, 0.0, None, warnings, pd.Series(dtype=float))
        k = 1.0 / tau_hours
        r2 = 0.0
        residuals = pd.Series(dtype=float)
        return DecayFitResult(k_per_hr=k, ach=k, baseline=baseline, r2=r2, ci=None, warnings=warnings, residuals=residuals)
    valid = (co2 > baseline)
    if valid.sum() < 3:
        warnings.append("Insufficient points above baseline")
        return DecayFitResult(0.0, 0.0, baseline, 0.0, None, warnings, pd.Series(dtype=float))

    t_hours = _to_hours(times[valid])
    y = np.log(co2[valid] - baseline)
    if method == "two_point":
        k = (y.iloc[0] - y.iloc[-1]) / (t_hours[-1] - t_hours[0])
        k = max(k, 0.0)
        yhat = y.iloc[0] - k * t_hours
    else:
        slope, intercept = np.polyfit(t_hours, y, 1)
        k = -slope
        yhat = intercept + slope * t_hours

    residuals = pd.Series(y - yhat, index=times[valid])
    r2 = _r2(y, yhat)

    if r2 < 0.6:
        warnings.append("Low R^2")

    return DecayFitResult(k_per_hr=k, ach=k, baseline=baseline, r2=r2, ci=None, warnings=warnings, residuals=residuals)


def fit_pn_decay(
    times: pd.Series,
    pn10: pd.Series,
    baseline: float,
    method: Literal["nonlinear", "log_linear"] = "nonlinear",
) -> DecayFitResult:
    warnings = []
    times = times.reset_index(drop=True)
    pn10 = pn10.reset_index(drop=True)
    valid = pn10.notna()

    if valid.sum() < 3:
        warnings.append("Insufficient points")
        return DecayFitResult(0.0, 0.0, baseline, 0.0, None, warnings, pd.Series(dtype=float))

    t_hours = _to_hours(times[valid])
    y = pn10[valid].to_numpy(dtype=float)

    if method == "log_linear":
        above = y > (baseline + 1e-9)
        if above.sum() < 3:
            warnings.append("Insufficient points above baseline")
            return DecayFitResult(0.0, 0.0, baseline, 0.0, None, warnings, pd.Series(dtype=float))
        ylog = np.log(y[above] - baseline)
        slope, intercept = np.polyfit(t_hours[above], ylog, 1)
        k = -slope
        yhat = baseline + np.exp(intercept + slope * t_hours)
    else:
        def model(t, a, k):
            return baseline + a * np.exp(-k * t)

        a0 = max(y[0] - baseline, 1e-6)
        k0 = 1.0
        try:
            params, _ = curve_fit(model, t_hours, y, p0=[a0, k0], maxfev=10000)
            a, k = params
            yhat = model(t_hours, a, k)
        except Exception:
            warnings.append("Nonlinear fit failed")
            return DecayFitResult(0.0, 0.0, baseline, 0.0, None, warnings, pd.Series(dtype=float))

    residuals = pd.Series(y - yhat, index=times[valid])
    r2 = _r2(y, yhat)
    if r2 < 0.6:
        warnings.append("Low R^2")

    return DecayFitResult(k_per_hr=k, ach=k, baseline=baseline, r2=r2, ci=None, warnings=warnings, residuals=residuals)


def detect_co2_decay_events(
    times: pd.Series,
    co2: pd.Series,
    baseline: float,
    min_drop: float = 100.0,
    min_minutes: float = 10.0,
    min_points: int = 4,
    min_gap_minutes: float = 5.0,
    method: Literal["regression", "two_point", "time_constant_63"] = "time_constant_63",
) -> list[DecayEvent]:
    df = pd.DataFrame({"time": times, "co2": co2}).dropna()
    if df.empty:
        return []
    df = df.sort_values("time").reset_index(drop=True)
    times = df["time"]
    co2 = df["co2"]

    excess = (co2 - baseline).to_numpy(dtype=float)
    if np.nanmax(excess) <= 0:
        return []

    events: list[DecayEvent] = []
    n = len(excess)
    if n < 3:
        return events

    smooth = pd.Series(excess).rolling(window=3, center=True, min_periods=1).median().to_numpy()
    peaks: list[int] = []
    troughs: list[int] = []
    if smooth[0] >= smooth[1] and smooth[0] >= min_drop:
        peaks.append(0)
    for i in range(1, n - 1):
        if smooth[i] >= smooth[i - 1] and smooth[i] > smooth[i + 1] and smooth[i] >= min_drop:
            peaks.append(i)
        if smooth[i] <= smooth[i - 1] and smooth[i] < smooth[i + 1]:
            troughs.append(i)

    last_end_time = None
    for peak_idx in peaks:
        peak_time = times.iloc[peak_idx]
        if last_end_time is not None and peak_time < last_end_time + pd.Timedelta(minutes=min_gap_minutes):
            continue

        # Find the next trough after the peak.
        next_trough = next((t for t in troughs if t > peak_idx), None)
        if next_trough is None:
            if peak_idx + 1 >= n:
                continue
            tail_idx = int(np.nanargmin(excess[peak_idx + 1 :])) + peak_idx + 1
            next_trough = tail_idx

        drop_amount = excess[peak_idx] - excess[next_trough]
        if drop_amount < min_drop:
            continue

        # Require a negative slope between peak and trough.
        t0 = times.iloc[peak_idx]
        t1 = times.iloc[next_trough]
        y0 = excess[peak_idx]
        y1 = excess[next_trough]
        if (t1 - t0).total_seconds() <= 0:
            continue
        slope_per_hour = (y1 - y0) / ((t1 - t0).total_seconds() / 3600.0)
        if slope_per_hour >= 0:
            continue

        peak_val = excess[peak_idx]
        end_idx = None
        reached_1e = False
        for j in range(peak_idx + 1, next_trough + 1):
            if np.isnan(excess[j]):
                continue
            if excess[j] <= peak_val / np.e:
                end_idx = j
                reached_1e = True
                break

        if end_idx is None:
            end_idx = next_trough

        start_time = peak_time
        end_time = times.iloc[end_idx]
        duration = end_time - start_time
        if duration < pd.Timedelta(minutes=min_minutes):
            continue

        if (end_idx - peak_idx + 1) < min_points:
            continue

        segment_times = times.iloc[peak_idx : end_idx + 1]
        segment_co2 = co2.iloc[peak_idx : end_idx + 1]
        fit_method = method
        warnings = []
        if not reached_1e and method == "time_constant_63":
            fit_method = "regression"
            warnings.append("Did not reach 1/e before next rise; used regression")
        result = fit_co2_decay(segment_times, segment_co2, baseline, method=fit_method)
        warnings.extend(result.warnings)

        label = f"E{len(events) + 1}"
        events.append(
            DecayEvent(
                label=label,
                start=start_time,
                end=end_time,
                peak_time=peak_time,
                peak_value=float(co2.iloc[peak_idx]),
                baseline=baseline,
                method=fit_method,
                ach=result.ach,
                r2=result.r2,
                warnings=warnings,
            )
        )
        last_end_time = end_time

    return events


def summarize_ach(events: list[DecayEvent], min_r2: float = 0.9) -> dict[str, float]:
    values = [event.ach for event in events if event.r2 >= min_r2 and np.isfinite(event.ach)]
    if not values:
        return {}
    arr = np.array(values, dtype=float)
    std = float(np.std(arr, ddof=1)) if arr.size > 1 else 0.0
    return {
        "n": int(arr.size),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "std": std,
    }
