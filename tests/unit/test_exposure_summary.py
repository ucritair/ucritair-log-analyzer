import pandas as pd

from app.analysis.exposure import summarize_periods, exposure_stats


def test_summarize_periods_daily_auc():
    times = pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC")
    series = pd.Series([1.0, 1.0, 1.0, 1.0], index=times)
    summary = summarize_periods(series, threshold=0.5, freq="D")
    assert len(summary) == 1
    assert summary.iloc[0]["auc"] == 3 * 3600
    assert summary.iloc[0]["time_above_seconds"] == 3 * 3600


def test_exposure_stats_normalized():
    times = pd.date_range("2024-01-01", periods=4, freq="1h", tz="UTC")
    series = pd.Series([10.0, 10.0, 10.0, 10.0], index=times)
    stats = exposure_stats(series, threshold=5.0)
    assert stats["auc"] == 10.0 * 3 * 3600
    assert stats["mean"] == 10.0
    assert stats["relative_to_threshold"] == 2.0
    assert stats["time_above_pct"] == 100.0
