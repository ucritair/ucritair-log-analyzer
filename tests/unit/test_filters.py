import pandas as pd
import numpy as np

from app.analysis.filters import ema_time_aware, sma


def test_time_aware_ema_matches_expected_series():
    times = pd.to_datetime([0, 60, 120], unit="s", utc=True)
    series = pd.Series([0.0, 10.0, 10.0], index=times)
    out = ema_time_aware(series, tau=60)
    assert np.isclose(out.iloc[0], 0.0)
    assert out.iloc[1] > 0.0
    assert out.iloc[2] > out.iloc[1]


def test_sma_numeric_string_uses_samples():
    times = pd.date_range("2024-01-01", periods=5, freq="1min", tz="UTC")
    series = pd.Series([0, 0, 10, 10, 10], index=times)
    out = sma(series, "3")
    assert len(out) == 5
    assert out.iloc[2] > 0


def test_ema_numeric_string_uses_seconds():
    times = pd.to_datetime([0, 60, 120], unit="s", utc=True)
    series = pd.Series([0.0, 10.0, 10.0], index=times)
    out_num = ema_time_aware(series, tau=60)
    out_str = ema_time_aware(series, tau="60")
    assert np.isclose(out_num.iloc[1], out_str.iloc[1])
