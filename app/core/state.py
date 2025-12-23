from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from PySide6.QtCore import QThreadPool

from app.core.config import ProcessingConfig, FilterConfig


@dataclass
class AppState:
    datasets: list[Any]
    active_standard_pack: str
    tz_display: str
    processing_config: ProcessingConfig
    filter_config: FilterConfig
    threadpool: QThreadPool
    time_range: tuple[Any, Any] | None = None
