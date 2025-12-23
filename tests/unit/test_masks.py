import pandas as pd

from app.core.config import ProcessingConfig
from app.data.mask_rules import apply_validity_masks


def test_pm_pn_zeros_remain_valid():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime([0, 60], unit="s", utc=True),
        "pm2_5": [0.0, 5.0],
        "pn10_0": [0.0, 10.0],
    })
    cfg = ProcessingConfig()
    result = apply_validity_masks(df, cfg)
    assert result.masks["pm2_5"].all()
    assert result.masks["pn10_0"].all()


def test_voc_nox_zero_masked_by_default():
    df = pd.DataFrame({
        "timestamp": pd.to_datetime([0, 60], unit="s", utc=True),
        "voc": [0.0, 10.0],
        "nox": [0.0, 5.0],
    })
    cfg = ProcessingConfig()
    result = apply_validity_masks(df, cfg)
    assert result.masks["voc"].tolist() == [False, True]
    assert result.masks["nox"].tolist() == [False, True]
