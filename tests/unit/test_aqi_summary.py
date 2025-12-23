import pandas as pd

from app.analysis.aqi import aqi_summary


def test_aqi_summary_time_in_category():
    times = pd.date_range("2024-01-01", periods=3, freq="1min", tz="UTC")
    series = pd.Series([10, 20, 30], index=times)
    categories = [
        {"name": "Low", "low": 0, "high": 15},
        {"name": "High", "low": 16, "high": 50},
    ]
    summary = aqi_summary(series, categories)
    assert summary["time_Low"] == 0.0
    assert summary["time_High"] == 120.0
