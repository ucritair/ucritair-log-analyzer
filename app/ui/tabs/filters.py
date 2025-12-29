from __future__ import annotations

from PySide6 import QtWidgets, QtCore

from app.core.state import AppState


class FiltersTab(QtWidgets.QWidget):
    filters_changed = QtCore.Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Use smoothing to reduce noise. Smoothing changes what you see, "
            "but it does not alter the raw data."
        )
        intro.setWordWrap(True)
        intro.setObjectName("introText")
        layout.addWidget(intro)

        smoothing_group = QtWidgets.QGroupBox("Smoothing settings")
        form = QtWidgets.QFormLayout(smoothing_group)

        self.sma_input = QtWidgets.QLineEdit()
        self.sma_input.setPlaceholderText("e.g., 10 samples or 30min")
        self.sma_input.setToolTip("Use samples (e.g., 10) or a time like 30min.")
        self.ema_input = QtWidgets.QLineEdit()
        self.ema_input.setPlaceholderText("e.g., 15min")
        self.ema_input.setToolTip("Use seconds (e.g., 60) or a time like 15min.")
        self.nan_mode = QtWidgets.QComboBox()
        self.nan_mode.addItem("Skip gaps (keep previous value)", "skip")
        self.nan_mode.addItem("Reset at gaps (start fresh)", "reset")
        self.nan_mode.addItem("Hold last value through gaps", "hold")
        self.nan_mode.setToolTip("How smoothing behaves when data has gaps.")
        self.apply_btn = QtWidgets.QPushButton("Apply smoothing")
        self.apply_btn.setToolTip("Apply smoothing to the current plot.")
        self.apply_btn.setObjectName("primaryButton")

        form.addRow("Moving average window", self.sma_input)
        form.addRow("Exponential smoothing time", self.ema_input)
        form.addRow("Gaps in data", self.nan_mode)
        layout.addWidget(smoothing_group)
        layout.addWidget(self.apply_btn)

        self.apply_btn.clicked.connect(self._apply)

    def _apply(self):
        sma_text = self.sma_input.text().strip()
        ema_text = self.ema_input.text().strip()

        self.state.filter_config.sma_window = sma_text or None
        self.state.filter_config.ema_tau = ema_text or None
        self.state.filter_config.ema_nan_mode = self.nan_mode.currentData() or self.nan_mode.currentText()
        self.filters_changed.emit()

    def set_config(self, config):
        self.sma_input.setText("" if config.sma_window is None else str(config.sma_window))
        self.ema_input.setText("" if config.ema_tau is None else str(config.ema_tau))
        idx = self.nan_mode.findData(config.ema_nan_mode)
        if idx >= 0:
            self.nan_mode.setCurrentIndex(idx)
