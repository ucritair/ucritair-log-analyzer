from __future__ import annotations

from PySide6 import QtWidgets, QtCore
import pandas as pd

from app.ui.models import PandasTableModel


class DataTableTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel("Browse the data in a table view.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        controls = QtWidgets.QHBoxLayout()
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["Cleaned data", "Raw data", "Resampled data"])
        self.mode_combo.setToolTip("Choose which version of the data to show.")
        self.selection_only = QtWidgets.QCheckBox("Use selected time window only")
        self.selection_only.setToolTip("Use the time window from the Plot tab.")
        controls.addWidget(self.mode_combo)
        controls.addWidget(self.selection_only)
        controls.addStretch(1)

        self.table = QtWidgets.QTableView()
        self.model = PandasTableModel(pd.DataFrame())
        self.table.setModel(self.model)

        layout.addLayout(controls)
        layout.addWidget(self.table)

        self.dataset = None
        self.time_range = None

        self.mode_combo.currentTextChanged.connect(self._refresh)
        self.selection_only.toggled.connect(self._refresh)

    def set_dataset(self, dataset):
        self.dataset = dataset
        self._refresh()

    def set_time_range(self, start, end):
        if start is None or end is None:
            self.time_range = None
        else:
            self.time_range = (start, end)
        self._refresh()

    def _active_df(self):
        if self.dataset is None:
            return pd.DataFrame()
        mode = self.mode_combo.currentText()
        if mode == "Raw data":
            df = self.dataset.raw
        elif mode == "Resampled data":
            df = self.dataset.resampled if self.dataset.resampled is not None else self.dataset.clean
        else:
            df = self.dataset.clean

        if self.selection_only.isChecked() and self.time_range is not None and "timestamp" in df.columns:
            start, end = self.time_range
            mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
            df = df.loc[mask]
        return df

    def _refresh(self):
        df = self._active_df()
        self.model.set_dataframe(df)
