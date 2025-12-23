from pathlib import Path

import pandas as pd

from app.analysis.aqi import load_standard_pack, compute_aqi


def _series(value: float) -> pd.Series:
    idx = pd.to_datetime([0], unit="s", utc=True)
    return pd.Series([value], index=idx)


def test_uk_defra_daqi_pm25_band():
    pack = load_standard_pack(Path("app/resources/standards/uk_defra_daqi.yaml"))
    pm25 = _series(12.0)
    aqi_df = compute_aqi(pm25, None, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 2.0


def test_uk_defra_daqi_pm10_band():
    pack = load_standard_pack(Path("app/resources/standards/uk_defra_daqi.yaml"))
    pm10 = _series(17.0)
    aqi_df = compute_aqi(None, pm10, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 2.0


def test_uk_defra_daqi_truncation_to_integer_band():
    pack = load_standard_pack(Path("app/resources/standards/uk_defra_daqi.yaml"))
    pm25 = _series(12.9)
    aqi_df = compute_aqi(pm25, None, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 2.0


def test_us_epa_legacy_pm25_boundary_and_truncation():
    pack = load_standard_pack(Path("app/resources/standards/us_epa_legacy.yaml"))
    pm25 = pd.Series(
        [12.04, 12.0, 12.1],
        index=pd.to_datetime([0, 1, 2], unit="s", utc=True),
    )
    aqi_df = compute_aqi(pm25, None, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 50.0
    assert float(aqi_df["aqi_overall"].iloc[1]) == 50.0
    assert float(aqi_df["aqi_overall"].iloc[2]) == 51.0


def test_us_epa_2024_pm25_boundary_and_truncation():
    pack = load_standard_pack(Path("app/resources/standards/us_epa_2024.yaml"))
    pm25 = pd.Series(
        [9.04, 9.0, 9.1],
        index=pd.to_datetime([0, 1, 2], unit="s", utc=True),
    )
    aqi_df = compute_aqi(pm25, None, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 50.0
    assert float(aqi_df["aqi_overall"].iloc[1]) == 50.0
    assert float(aqi_df["aqi_overall"].iloc[2]) == 51.0


def test_eu_eea_pm25_band():
    pack = load_standard_pack(Path("app/resources/standards/eu_eea.yaml"))
    pm25 = _series(12.0)
    aqi_df = compute_aqi(pm25, None, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 2.0


def test_who_guideline_pm25_band():
    pack = load_standard_pack(Path("app/resources/standards/who_guideline.yaml"))
    pm25 = _series(15.0)
    aqi_df = compute_aqi(pm25, None, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 1.0


def test_india_cpcb_aqi_pm25_boundary():
    pack = load_standard_pack(Path("app/resources/standards/in_cpcb_aqi.yaml"))
    pm25 = _series(30.0)
    aqi_df = compute_aqi(pm25, None, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 50.0


def test_india_cpcb_aqi_pm10_boundary():
    pack = load_standard_pack(Path("app/resources/standards/in_cpcb_aqi.yaml"))
    pm10 = _series(100.0)
    aqi_df = compute_aqi(None, pm10, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 100.0


def test_china_mee_aqi_pm10_boundary():
    pack = load_standard_pack(Path("app/resources/standards/cn_mee_aqi.yaml"))
    pm10 = _series(150.0)
    aqi_df = compute_aqi(None, pm10, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 100.0


def test_china_mee_aqi_pm25_boundary():
    pack = load_standard_pack(Path("app/resources/standards/cn_mee_aqi.yaml"))
    pm25 = _series(35.0)
    aqi_df = compute_aqi(pm25, None, pack)
    assert float(aqi_df["aqi_overall"].iloc[0]) == 50.0
