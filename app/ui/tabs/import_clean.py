from __future__ import annotations

from PySide6 import QtWidgets, QtCore
import pandas as pd

from app.core.state import AppState
from app.core.config import ProcessingConfig


class ImportCleanTab(QtWidgets.QWidget):
    config_changed = QtCore.Signal()

    def __init__(self, state: AppState):
        super().__init__()
        self.state = state

        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Review the loaded file and choose how to clean it. "
            "Changes apply to the current dataset."
        )
        intro.setWordWrap(True)
        intro.setObjectName("introText")
        layout.addWidget(intro)

        summary_group = QtWidgets.QGroupBox("Current file summary")
        summary_layout = QtWidgets.QVBoxLayout(summary_group)
        self.summary_label = QtWidgets.QLabel("No file loaded.")
        self.summary_label.setWordWrap(True)
        summary_layout.addWidget(self.summary_label)
        layout.addWidget(summary_group)

        cleaning_group = QtWidgets.QGroupBox("Cleaning options")
        cleaning_layout = QtWidgets.QFormLayout(cleaning_group)

        self.voc_mask_checkbox = QtWidgets.QCheckBox("Ignore gas index zeros (sensor off)")
        self.voc_mask_checkbox.setToolTip(
            "When unchecked, VOC/NOx zeros are kept in the data and plots."
        )
        self.voc_mask_checkbox.setChecked(True)
        self.flatline_checkbox = QtWidgets.QCheckBox("Flag constant particle readings")
        self.flatline_checkbox.setToolTip(
            "Highlights long, constant segments in particle data without removing them."
        )
        self.flatline_checkbox.setChecked(True)
        self.flatline_mask_checkbox = QtWidgets.QCheckBox("Hide flagged particle flatlines")
        self.flatline_mask_checkbox.setToolTip(
            "When enabled, flagged flatlines are removed from plots and calculations."
        )
        self.flatline_mask_checkbox.setChecked(False)

        cleaning_layout.addRow(self.voc_mask_checkbox)
        cleaning_layout.addRow(self.flatline_checkbox)
        cleaning_layout.addRow(self.flatline_mask_checkbox)
        layout.addWidget(cleaning_group)

        sampling_group = QtWidgets.QGroupBox("Resampling")
        sampling_layout = QtWidgets.QFormLayout(sampling_group)
        self.resample_input = QtWidgets.QLineEdit()
        self.resample_input.setPlaceholderText("e.g., 3min")
        self.resample_input.setToolTip("Optional. Enter a new spacing such as 3min, 10s, or 1H.")
        self.use_resampled_checkbox = QtWidgets.QCheckBox("Use resampled data in plots and calculations")
        self.use_resampled_checkbox.setToolTip(
            "If enabled, the app uses the resampled data instead of the original timestamps."
        )
        self.use_resampled_checkbox.setChecked(False)

        self.apply_btn = QtWidgets.QPushButton("Apply to current dataset")
        self.apply_btn.setObjectName("primaryButton")
        self.apply_btn.setToolTip("Apply these settings to the current dataset.")

        sampling_layout.addRow("Resample spacing", self.resample_input)
        sampling_layout.addRow(self.use_resampled_checkbox)
        layout.addWidget(sampling_group)
        layout.addWidget(self.apply_btn)

        self.apply_btn.clicked.connect(self._apply)
        self.flatline_checkbox.toggled.connect(self._sync_flatline_controls)
        self._sync_flatline_controls()

    def _apply(self):
        self.state.processing_config.voc_nox_zero_mode = (
            "mask_inactive" if self.voc_mask_checkbox.isChecked() else "keep_raw"
        )
        self.state.processing_config.flatline_diag_enabled = self.flatline_checkbox.isChecked()
        self.state.processing_config.flatline_automask = self.flatline_mask_checkbox.isChecked()
        self.state.processing_config.resample_interval = self.resample_input.text().strip() or None
        self.state.processing_config.use_resampled = self.use_resampled_checkbox.isChecked()
        self.config_changed.emit()

    def set_dataset(self, dataset):
        self.voc_mask_checkbox.setChecked(self.state.processing_config.voc_nox_zero_mode == "mask_inactive")
        self.flatline_checkbox.setChecked(self.state.processing_config.flatline_diag_enabled)
        self.flatline_mask_checkbox.setChecked(self.state.processing_config.flatline_automask)
        self.resample_input.setText(self.state.processing_config.resample_interval or "")
        self.use_resampled_checkbox.setChecked(self.state.processing_config.use_resampled)
        self._sync_flatline_controls()
        self._update_summary(dataset)

    def _sync_flatline_controls(self):
        enabled = self.flatline_checkbox.isChecked()
        self.flatline_mask_checkbox.setEnabled(enabled)

    def _update_summary(self, dataset):
        if dataset is None:
            self.summary_label.setText("No file loaded.")
            return
        df = dataset.clean
        if df.empty:
            self.summary_label.setText("This file has no rows after cleaning.")
            return
        start = df["timestamp"].min()
        end = df["timestamp"].max()
        duration = end - start
        samples = len(df)
        median_dt = df["timestamp"].diff().median()
        median_text = "n/a" if pd.isna(median_dt) else str(median_dt)
        gaps = dataset.metadata.get("gaps", [])
        gap_count = len(gaps)
        text = (
            f"Time range: {start} to {end} (duration {duration})\n"
            f"Samples: {samples} | Typical spacing: {median_text}\n"
            f"Detected gaps: {gap_count}"
        )
        self.summary_label.setText(text)
