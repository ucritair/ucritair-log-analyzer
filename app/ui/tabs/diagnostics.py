from __future__ import annotations

from PySide6 import QtWidgets
import pandas as pd


class DiagnosticsTab(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Quality checks help you spot gaps, flatlines, and data that was masked."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        self.gaps_table = QtWidgets.QTableWidget(0, 2)
        self.gaps_table.setHorizontalHeaderLabels(["Gap start", "Gap end"])
        self.gaps_table.horizontalHeader().setStretchLastSection(True)
        self.gaps_table.verticalHeader().setVisible(False)

        self.flat_table = QtWidgets.QTableWidget(0, 2)
        self.flat_table.setHorizontalHeaderLabels(["Metric", "Flatline count"])
        self.flat_table.horizontalHeader().setStretchLastSection(True)
        self.flat_table.verticalHeader().setVisible(False)

        self.flags_table = QtWidgets.QTableWidget(0, 3)
        self.flags_table.setHorizontalHeaderLabels(["Flag value", "Binary", "Count"])
        self.flags_table.horizontalHeader().setStretchLastSection(True)
        self.flags_table.verticalHeader().setVisible(False)

        self.reasons_table = QtWidgets.QTableWidget(0, 3)
        self.reasons_table.setHorizontalHeaderLabels(["Metric", "Reason", "Count"])
        self.reasons_table.horizontalHeader().setStretchLastSection(True)
        self.reasons_table.verticalHeader().setVisible(False)

        gaps_group = QtWidgets.QGroupBox("Detected gaps")
        gaps_layout = QtWidgets.QVBoxLayout(gaps_group)
        gaps_layout.addWidget(self.gaps_table)

        flat_group = QtWidgets.QGroupBox("Flatline checks")
        flat_layout = QtWidgets.QVBoxLayout(flat_group)
        flat_layout.addWidget(self.flat_table)

        flags_group = QtWidgets.QGroupBox("Device flags")
        flags_layout = QtWidgets.QVBoxLayout(flags_group)
        flags_layout.addWidget(self.flags_table)

        reasons_group = QtWidgets.QGroupBox("Why values were masked")
        reasons_layout = QtWidgets.QVBoxLayout(reasons_group)
        reasons_layout.addWidget(self.reasons_table)

        layout.addWidget(gaps_group)
        layout.addWidget(flat_group)
        layout.addWidget(flags_group)
        layout.addWidget(reasons_group)

    def set_dataset(self, dataset):
        if dataset is None:
            return
        self._render_gaps(dataset.metadata.get("gaps", []))
        self._render_flatlines(dataset.flags)
        self._render_flags(dataset.raw)
        self._render_reasons(dataset.metadata.get("mask_reasons", {}))

    def _render_gaps(self, gaps):
        self.gaps_table.setRowCount(0)
        for row, (start, end) in enumerate(gaps):
            self.gaps_table.insertRow(row)
            self.gaps_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(start)))
            self.gaps_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(end)))

    def _render_flatlines(self, flags):
        self.flat_table.setRowCount(0)
        for row, (metric, mask) in enumerate(flags.items()):
            count = int(mask.sum()) if hasattr(mask, "sum") else 0
            self.flat_table.insertRow(row)
            self.flat_table.setItem(row, 0, QtWidgets.QTableWidgetItem(metric))
            self.flat_table.setItem(row, 1, QtWidgets.QTableWidgetItem(str(count)))

    def _render_flags(self, df):
        self.flags_table.setRowCount(0)
        if df is None or "flags" not in df.columns:
            return
        counts = df["flags"].value_counts().sort_index()
        for row_idx, (value, count) in enumerate(counts.items()):
            self.flags_table.insertRow(row_idx)
            self.flags_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(value)))
            binary = format(int(value), "08b") if pd.notna(value) else ""
            self.flags_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(binary))
            self.flags_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(int(count))))

    def _render_reasons(self, reasons):
        self.reasons_table.setRowCount(0)
        row_idx = 0
        for metric, reason_map in reasons.items():
            for reason, count in reason_map.items():
                self.reasons_table.insertRow(row_idx)
                self.reasons_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(metric))
                self.reasons_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(reason))
                self.reasons_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(count)))
                row_idx += 1
