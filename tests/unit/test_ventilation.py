import pandas as pd
import numpy as np

from app.analysis.ventilation import (
    fit_co2_decay,
    fit_pn_decay,
    detect_co2_decay_events,
    summarize_ach,
    DecayEvent,
)


def test_co2_decay_fit_noise():
    times = pd.date_range("2024-01-01", periods=6, freq="5min", tz="UTC")
    baseline = 400.0
    k = 1.0
    t_hours = np.arange(6) * (5 / 60)
    co2 = baseline + 200 * np.exp(-k * t_hours)
    series = pd.Series(co2, index=times)

    result = fit_co2_decay(series.index.to_series(), series, baseline, method="regression")
    assert result.ach > 0


def test_pn_decay_nonlinear_handles_zeros():
    times = pd.date_range("2024-01-01", periods=6, freq="5min", tz="UTC")
    baseline = 0.0
    pn = pd.Series([100, 80, 60, 40, 20, 0], index=times)
    result = fit_pn_decay(times.to_series(), pn, baseline, method="nonlinear")
    assert result.ach >= 0


def test_co2_time_constant_63():
    times = pd.date_range("2024-01-01", periods=2, freq="1h", tz="UTC")
    baseline = 400.0
    peak_excess = 1000.0
    co2 = [baseline + peak_excess, baseline + peak_excess / np.e]
    series = pd.Series(co2, index=times)
    result = fit_co2_decay(series.index.to_series(), series, baseline, method="time_constant_63")
    assert np.isclose(result.ach, 1.0, atol=1e-3)


def test_detect_co2_decay_events_two():
    times = pd.date_range("2024-01-01", periods=61, freq="5min", tz="UTC")
    baseline = 400.0
    t_hours = np.arange(len(times)) * (5 / 60)
    co2 = np.full_like(t_hours, baseline, dtype=float)

    # Event 1: 0h to 1h
    mask1 = (t_hours >= 0) & (t_hours <= 1.0)
    co2[mask1] = baseline + 1000 * np.exp(-1.0 * (t_hours[mask1] - 0.0))

    # Event 2: 2h to 3h
    mask2 = (t_hours >= 2.0) & (t_hours <= 3.0)
    co2[mask2] = baseline + 800 * np.exp(-1.0 * (t_hours[mask2] - 2.0))

    series = pd.Series(co2, index=times)
    events = detect_co2_decay_events(
        series.index.to_series(),
        series,
        baseline,
        min_drop=300,
        min_minutes=10,
        method="time_constant_63",
    )
    assert len(events) == 2
    assert events[0].label == "E1"
    assert events[1].label == "E2"


def test_summarize_ach_filters_r2():
    t0 = pd.Timestamp("2024-01-01", tz="UTC")
    events = [
        DecayEvent("E1", t0, t0, t0, 1000.0, 400.0, "regression", 0.5, 0.95, []),
        DecayEvent("E2", t0, t0, t0, 1000.0, 400.0, "regression", 1.0, 0.85, []),
        DecayEvent("E3", t0, t0, t0, 1000.0, 400.0, "regression", 1.5, 0.99, []),
    ]
    stats = summarize_ach(events, min_r2=0.9)
    assert stats["n"] == 2
    assert np.isclose(stats["mean"], 1.0)
    assert np.isclose(stats["median"], 1.0)
    assert np.isclose(stats["min"], 0.5)
    assert np.isclose(stats["max"], 1.5)
    assert np.isclose(stats["std"], 0.70710678, atol=1e-6)
