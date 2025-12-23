from pathlib import Path

import pytest

from app.core.config import ProcessingConfig, FilterConfig
from app.data.importer import DatasetImporter
from app.analysis.aqi import load_standard_pack, compute_aqi, apply_averaging
from app.persistence.project import Project, save_project, load_project


ROOT = Path(__file__).resolve().parents[2]
SAMPLE_CASES = [
    {
        "id": "sample_data_1",
        "path": ROOT / "sample_data_1.csv",
        "rows": 6881,
        "gaps": 35,
        "pm2_5_max": 28.0,
        "pn10_0_max": 204.89,
        "median_dt": 198,
        "voc_inactive_zero": 5740,
        "nox_inactive_zero": 5739,
        "voc_nonzero": 1141,
        "nox_nonzero": 1142,
        "resampled_rows": 16397,
        "resampled_median_dt": 180,
        "aqi_max": 84.0,
        "aqi_min": 0.0,
        "daily_rows": 35,
        "daily_max": 8.0,
        "flatline_count": 504,
    },
    {
        "id": "sample_data_2",
        "path": ROOT / "sample_data_2.csv",
        "rows": 10688,
        "gaps": 26,
        "pm2_5_max": 655.2,
        "pn10_0_max": 655.2,
        "median_dt": 198,
        "voc_inactive_zero": 9986,
        "nox_inactive_zero": 9995,
        "voc_nonzero": 702,
        "nox_nonzero": 693,
        "resampled_rows": 177748,
        "resampled_median_dt": 180,
        "aqi_max": 467.0,
        "aqi_min": 0.0,
        "daily_rows": 371,
        "daily_max": 81.0,
        "flatline_count": 810,
    },
]


@pytest.fixture(params=SAMPLE_CASES, ids=[case["id"] for case in SAMPLE_CASES])
def sample_case(request):
    return request.param


@pytest.fixture(scope="module")
def importer():
    return DatasetImporter()


@pytest.fixture
def dataset(importer, sample_case):
    return importer.load_csv(sample_case["path"], ProcessingConfig())


@pytest.fixture
def dataset_resampled(importer, sample_case):
    return importer.load_csv(sample_case["path"], ProcessingConfig(resample_interval="3min"))


def test_import_sample_basic_shape(dataset, sample_case):
    assert len(dataset.raw) == sample_case["rows"]
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


def test_sample_gap_detection(dataset, sample_case):
    gaps = dataset.metadata.get("gaps", [])
    assert len(gaps) == sample_case["gaps"]
    assert all(start < end for start, end in gaps)


def test_sample_voc_nox_zero_masking(dataset, sample_case):
    raw = dataset.raw
    masks = dataset.masks

    voc_zero = raw["voc"] == 0
    nox_zero = raw["nox"] == 0

    assert voc_zero.any()
    assert nox_zero.any()
    assert (~masks["voc"][voc_zero]).all()
    assert (~masks["nox"][nox_zero]).all()

    assert masks["voc"][~voc_zero].all()
    assert masks["nox"][~nox_zero].all()

    assert int((raw["voc"] != 0).sum()) == sample_case["voc_nonzero"]
    assert int((raw["nox"] != 0).sum()) == sample_case["nox_nonzero"]


def test_sample_pm_pn_zero_valid(dataset):
    raw = dataset.raw
    masks = dataset.masks

    pm_zero = raw["pm2_5"] == 0
    pn_zero = raw["pn10_0"] == 0

    assert pm_zero.any()
    assert pn_zero.any()
    assert masks["pm2_5"][pm_zero].all()
    assert masks["pn10_0"][pn_zero].all()


def test_sample_ranges_cadence(dataset, sample_case):
    raw = dataset.raw
    assert raw["pm2_5"].max() == pytest.approx(sample_case["pm2_5_max"])
    assert raw["pn10_0"].max() == pytest.approx(sample_case["pn10_0_max"])

    deltas = raw["timestamp"].diff().dropna().dt.total_seconds()
    assert int(deltas.median()) == sample_case["median_dt"]


def test_sample_mask_reason_counts(dataset, sample_case):
    reasons = dataset.metadata.get("mask_reasons", {})
    assert reasons["voc"]["inactive_zero"] == sample_case["voc_inactive_zero"]
    assert reasons["nox"]["inactive_zero"] == sample_case["nox_inactive_zero"]


def test_sample_resample_interval(dataset_resampled, sample_case):
    resampled = dataset_resampled.resampled
    assert resampled is not None
    assert len(resampled) == sample_case["resampled_rows"]
    deltas = resampled["timestamp"].diff().dropna().dt.total_seconds()
    assert int(deltas.median()) == sample_case["resampled_median_dt"]


def test_sample_aqi_max_legacy(dataset, sample_case):
    pack = load_standard_pack(ROOT / "app" / "resources" / "standards" / "us_epa_legacy.yaml")
    df = dataset.clean.set_index("timestamp")
    aqi_df = compute_aqi(df.get("pm2_5"), df.get("pm10"), pack)
    assert float(aqi_df["aqi_overall"].max()) == pytest.approx(sample_case["aqi_max"])
    assert float(aqi_df["aqi_overall"].min()) == pytest.approx(sample_case["aqi_min"])


def test_sample_aqi_daily_averaging(dataset, sample_case):
    pack = load_standard_pack(ROOT / "app" / "resources" / "standards" / "us_epa_legacy.yaml")
    df = dataset.clean.set_index("timestamp")
    pm25 = apply_averaging(df.get("pm2_5"), "daily")
    pm10 = apply_averaging(df.get("pm10"), "daily")
    aqi_df = compute_aqi(pm25, pm10, pack)
    assert len(aqi_df) == sample_case["daily_rows"]
    assert float(aqi_df["aqi_overall"].max()) == pytest.approx(sample_case["daily_max"])


def test_sample_flatline_diagnostics(dataset, sample_case):
    flags = dataset.flags
    assert "multi_channel_flatline" in flags
    assert int(flags["multi_channel_flatline"].sum()) == sample_case["flatline_count"]


def test_project_save_load_with_sample(tmp_path, sample_case):
    project = Project(
        dataset_paths=[str(sample_case["path"])],
        processing_config=ProcessingConfig(resample_interval="3min", use_resampled=True),
        filter_config=FilterConfig(sma_window="30min", ema_tau="15min"),
        active_standard_pack="us_epa_legacy",
        active_dataset_index=0,
    )
    path = tmp_path / "project.json"
    save_project(project, path)
    loaded = load_project(path)
    assert loaded.dataset_paths == [str(sample_case["path"])]
    assert loaded.processing_config.resample_interval == "3min"
    assert loaded.processing_config.use_resampled is True
    assert loaded.filter_config.sma_window == "30min"
    assert loaded.filter_config.ema_tau == "15min"
