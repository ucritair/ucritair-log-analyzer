from pathlib import Path

import pytest

from app.core.config import ProcessingConfig, FilterConfig
from app.data.importer import DatasetImporter
from app.analysis.aqi import load_standard_pack, compute_aqi, apply_averaging
from app.persistence.project import Project, save_project, load_project


LOG_PATH = Path(__file__).resolve().parents[2] / "LOG_0.CSV"


@pytest.fixture(scope="module")
def log_dataset():
    importer = DatasetImporter()
    return importer.load_csv(LOG_PATH, ProcessingConfig())


@pytest.fixture(scope="module")
def log_dataset_resampled():
    importer = DatasetImporter()
    return importer.load_csv(LOG_PATH, ProcessingConfig(resample_interval="3min"))


def test_import_log_0_basic_shape(log_dataset):
    dataset = log_dataset
    assert len(dataset.raw) == 6881
    assert dataset.raw["timestamp"].is_monotonic_increasing
    assert dataset.raw["timestamp"].dt.tz is not None

    expected_cols = {
        "timestamp",
        "flags",
        "co2",
        "co2_uncomp",
        "pm1_0",
        "pm2_5",
        "pm4_0",
        "pm10",
        "pn0_5",
        "pn1_0",
        "pn2_5",
        "pn4_0",
        "pn10_0",
        "temp_c",
        "rh",
        "voc",
        "nox",
        "pressure",
    }
    assert expected_cols.issubset(set(dataset.raw.columns))


def test_log_0_gap_detection(log_dataset):
    gaps = log_dataset.metadata.get("gaps", [])
    assert len(gaps) == 35
    assert all(start < end for start, end in gaps)


def test_log_0_voc_nox_zero_masking(log_dataset):
    raw = log_dataset.raw
    masks = log_dataset.masks

    voc_zero = raw["voc"] == 0
    nox_zero = raw["nox"] == 0

    assert voc_zero.any()
    assert nox_zero.any()
    assert (~masks["voc"][voc_zero]).all()
    assert (~masks["nox"][nox_zero]).all()

    assert masks["voc"][~voc_zero].all()
    assert masks["nox"][~nox_zero].all()

    assert int((raw["voc"] != 0).sum()) == 1141
    assert int((raw["nox"] != 0).sum()) == 1142


def test_log_0_pm_pn_zero_valid(log_dataset):
    raw = log_dataset.raw
    masks = log_dataset.masks

    pm_zero = raw["pm2_5"] == 0
    pn_zero = raw["pn10_0"] == 0

    assert pm_zero.any()
    assert pn_zero.any()
    assert masks["pm2_5"][pm_zero].all()
    assert masks["pn10_0"][pn_zero].all()


def test_log_0_ranges_cadence(log_dataset):
    raw = log_dataset.raw
    assert raw["pm2_5"].max() == 28.0
    assert raw["pn10_0"].max() == 204.89

    deltas = raw["timestamp"].diff().dropna().dt.total_seconds()
    assert int(deltas.median()) == 198


def test_log_0_mask_reason_counts(log_dataset):
    reasons = log_dataset.metadata.get("mask_reasons", {})
    assert reasons["voc"]["inactive_zero"] == 5740
    assert reasons["nox"]["inactive_zero"] == 5739


def test_log_0_resample_interval(log_dataset_resampled):
    resampled = log_dataset_resampled.resampled
    assert resampled is not None
    assert len(resampled) == 16397
    deltas = resampled["timestamp"].diff().dropna().dt.total_seconds()
    assert int(deltas.median()) == 180


def test_log_0_aqi_max_legacy(log_dataset):
    pack = load_standard_pack(LOG_PATH.parent / "app" / "resources" / "standards" / "us_epa_legacy.yaml")
    df = log_dataset.clean.set_index("timestamp")
    aqi_df = compute_aqi(df.get("pm2_5"), df.get("pm10"), pack)
    assert float(aqi_df["aqi_overall"].max()) == 84.0
    assert float(aqi_df["aqi_overall"].min()) == 0.0


def test_log_0_aqi_daily_averaging(log_dataset):
    pack = load_standard_pack(LOG_PATH.parent / "app" / "resources" / "standards" / "us_epa_legacy.yaml")
    df = log_dataset.clean.set_index("timestamp")
    pm25 = apply_averaging(df.get("pm2_5"), "daily")
    pm10 = apply_averaging(df.get("pm10"), "daily")
    aqi_df = compute_aqi(pm25, pm10, pack)
    assert len(aqi_df) == 35
    assert float(aqi_df["aqi_overall"].max()) == 8.0


def test_log_0_flatline_diagnostics(log_dataset):
    flags = log_dataset.flags
    assert "multi_channel_flatline" in flags
    assert int(flags["multi_channel_flatline"].sum()) == 504


def test_project_save_load_with_log_0(tmp_path):
    project = Project(
        dataset_paths=[str(LOG_PATH)],
        processing_config=ProcessingConfig(resample_interval="3min", use_resampled=True),
        filter_config=FilterConfig(sma_window="30min", ema_tau="15min"),
        active_standard_pack="us_epa_legacy",
        active_dataset_index=0,
    )
    path = tmp_path / "project.json"
    save_project(project, path)
    loaded = load_project(path)
    assert loaded.dataset_paths == [str(LOG_PATH)]
    assert loaded.processing_config.resample_interval == "3min"
    assert loaded.processing_config.use_resampled is True
    assert loaded.filter_config.sma_window == "30min"
    assert loaded.filter_config.ema_tau == "15min"
