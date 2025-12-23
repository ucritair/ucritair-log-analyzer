from __future__ import annotations

from dataclasses import dataclass
import pandas as pd

from app.core.config import ProcessingConfig


DEFAULT_RANGES = {
    "co2": (350.0, 20000.0),
    "temp_c": (-40.0, 85.0),
    "rh": (0.0, 100.0),
    "pressure": (300.0, 1100.0),
}

PM_COLUMNS = {"pm1_0", "pm2_5", "pm4_0", "pm10"}
PN_COLUMNS = {"pn0_5", "pn1_0", "pn2_5", "pn4_0", "pn10_0"}


@dataclass
class MaskResult:
    masks: dict[str, pd.Series]
    clean: pd.DataFrame
    reasons: dict[str, dict[str, int]]


def apply_validity_masks(df: pd.DataFrame, config: ProcessingConfig) -> MaskResult:
    masks: dict[str, pd.Series] = {}
    clean = df.copy()
    reasons: dict[str, dict[str, int]] = {}

    ranges = {**DEFAULT_RANGES, **config.plausible_ranges}

    for col in df.columns:
        if col == "timestamp":
            continue
        series = df[col]
        reasons[col] = {}
        is_null = series.isna()
        if is_null.any():
            reasons[col]["null"] = int(is_null.sum())
        valid = ~is_null

        if col == "flags":
            masks[col] = valid
            continue

        if col in PM_COLUMNS or col in PN_COLUMNS:
            neg = series < 0
            if neg.any():
                reasons[col]["negative"] = int(neg.sum())
            valid &= ~neg
        elif col == "voc" or col == "nox":
            neg = series < 0
            if neg.any():
                reasons[col]["negative"] = int(neg.sum())
            valid &= ~neg
            if config.voc_nox_zero_mode == "mask_inactive":
                zero = series == 0
                if zero.any():
                    reasons[col]["inactive_zero"] = int(zero.sum())
                valid &= ~zero
        elif col in ranges:
            lo, hi = ranges[col]
            below = series < lo
            above = series > hi
            if below.any():
                reasons[col]["below_min"] = int(below.sum())
            if above.any():
                reasons[col]["above_max"] = int(above.sum())
            valid &= ~below
            valid &= ~above
        elif col in ("co2_uncomp",):
            non_positive = series <= 0
            if non_positive.any():
                reasons[col]["non_positive"] = int(non_positive.sum())
            valid &= ~non_positive
        else:
            valid &= series.notna()

        masks[col] = valid
        clean.loc[~valid, col] = pd.NA

    return MaskResult(masks=masks, clean=clean, reasons=reasons)
