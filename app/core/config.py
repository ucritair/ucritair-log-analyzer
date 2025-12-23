from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ProcessingConfig:
    delimiter: str | None = None
    dedup_keep: Literal["first", "last"] = "first"
    gap_factor: float = 2.0
    resample_interval: str | None = None
    use_resampled: bool = False
    voc_nox_zero_mode: Literal["mask_inactive", "keep_raw"] = "mask_inactive"
    flatline_diag_enabled: bool = True
    flatline_automask: bool = False
    plausible_ranges: dict[str, tuple[float, float]] = field(default_factory=dict)


@dataclass
class FilterConfig:
    sma_window: str | int | None = None
    ema_tau: str | float | None = None
    ema_nan_mode: Literal["skip", "reset", "hold"] = "skip"
