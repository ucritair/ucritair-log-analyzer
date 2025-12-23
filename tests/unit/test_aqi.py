import pandas as pd

from app.analysis.aqi import compute_aqi, StandardPack, apply_averaging


def test_us_epa_legacy_vectors():
    pack = StandardPack(
        name="test",
        breakpoints={
            "pm25": [(0.0, 12.0, 0, 50)],
            "pm10": [(0.0, 54.0, 0, 50)],
        },
        rounding={"pm25": "round", "pm10": "round"},
    )
    pm25 = pd.Series([0.0, 12.0])
    pm10 = pd.Series([0.0, 54.0])
    df = compute_aqi(pm25, pm10, pack)
    assert df["aqi_pm25"].iloc[0] == 0
    assert df["aqi_pm25"].iloc[1] == 50
    assert df["aqi_pm10"].iloc[1] == 50


def test_aqi_truncation_applies():
    pack = StandardPack(
        name="test",
        breakpoints={"pm10": [(0.0, 54.0, 0, 50)]},
        rounding={"pm10": "round"},
        concentration_truncation={"pm10": 1},
    )
    pm10 = pd.Series([54.9])
    df = compute_aqi(None, pm10, pack)
    assert df["aqi_pm10"].iloc[0] == 50


def test_aqi_rounding_half_up():
    pack = StandardPack(
        name="test",
        breakpoints={"pm10": [(0.0, 100.0, 0, 100)]},
        rounding={"pm10": "round"},
    )
    pm10 = pd.Series([50.5])
    df = compute_aqi(None, pm10, pack)
    assert df["aqi_pm10"].iloc[0] == 51


def test_apply_averaging_rolling_and_daily():
    times = pd.date_range("2024-01-01", periods=3, freq="1h", tz="UTC")
    series = pd.Series([1.0, 2.0, 3.0], index=times)
    rolling = apply_averaging(series, "rolling_24h")
    assert rolling.iloc[-1] == 2.0
    daily = apply_averaging(series, "daily")
    assert len(daily) == 1
    assert float(daily.iloc[0]) == 2.0
