from __future__ import annotations

from PySide6 import QtWidgets, QtCore


class ExposureTab(QtWidgets.QWidget):
    compute_requested = QtCore.Signal(str, float, str, bool)

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Summarize exposure over time for a chosen measurement and threshold."
        )
        intro.setWordWrap(True)
        intro.setObjectName("introText")
        layout.addWidget(intro)

        form_group = QtWidgets.QGroupBox("Exposure settings")
        form = QtWidgets.QFormLayout(form_group)
        self.metric_combo = QtWidgets.QComboBox()
        self.metric_combo.setToolTip("Choose which measurement to analyze.")
        self.threshold_input = QtWidgets.QLineEdit("0")
        self.threshold_input.setPlaceholderText("e.g., 35")
        self.threshold_input.setToolTip("Threshold for time-above and exceedance calculations.")
        self.freq_combo = QtWidgets.QComboBox()
        self.freq_combo.addItems(["daily", "weekly", "monthly"])
        self.freq_combo.setToolTip("How to group the exposure summary.")
        self.selection_only = QtWidgets.QCheckBox("Use selected time window only")
        self.selection_only.setToolTip("Use the time window from the Plot tab.")
        self.compute_btn = QtWidgets.QPushButton("Compute exposure summary")
        self.compute_btn.setToolTip("Calculate exposure metrics and summaries.")
        self.compute_btn.setObjectName("primaryButton")
        self.result = QtWidgets.QLabel("No exposure computed")

        form.addRow("Metric", self.metric_combo)
        form.addRow("Threshold", self.threshold_input)
        form.addRow("Summary period", self.freq_combo)
        form.addRow(self.selection_only)
        form.addRow(self.compute_btn)

        self.summary_table = QtWidgets.QTableWidget(0, 6)
        self.summary_table.setHorizontalHeaderLabels(
            [
                "Start",
                "End",
                "Average level",
                "Relative to threshold",
                "Time above (%)",
                "Total exposure (raw)",
            ]
        )
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.verticalHeader().setVisible(False)
        self.range_label = QtWidgets.QLabel("Time window: full data")
        self._set_header_tooltips()

        layout.addWidget(form_group)
        layout.addWidget(self.result)
        layout.addWidget(self.range_label)
        layout.addWidget(self.summary_table)

        self.compute_btn.clicked.connect(self._emit_compute)

    def set_dataset(self, dataset):
        self.metric_combo.clear()
        if dataset is None:
            return
        from app.ui.metric_catalog import metric_display_name, sorted_metric_keys

        columns = [c for c in dataset.clean.columns if c != "timestamp"]
        for col in sorted_metric_keys(columns):
            self.metric_combo.addItem(metric_display_name(col), userData=col)

    def _emit_compute(self):
        metric = self.metric_combo.currentData() or self.metric_combo.currentText()
        try:
            threshold = float(self.threshold_input.text())
        except ValueError:
            threshold = 0.0
        freq = self.freq_combo.currentText()
        selection_only = self.selection_only.isChecked()
        self.compute_requested.emit(metric, threshold, freq, selection_only)

    def show_result(self, stats: dict, threshold: float):
        if not stats:
            self.result.setText("No exposure computed")
            return
        avg_text = self._fmt_float(stats.get("mean"))
        rel_text = self._fmt_ratio(stats.get("relative_to_threshold"))
        pct_text = self._fmt_percent(stats.get("time_above_pct"))
        avg_excess_text = self._fmt_float(stats.get("mean_excess"))
        parts = [
            f"Average level: {avg_text}",
            f"Relative to threshold ({threshold:g}): {rel_text}",
            f"Time above: {pct_text}",
            f"Average above threshold: {avg_excess_text}",
        ]
        self.result.setText(" | ".join(parts))

    def show_summary(self, summary_df):
        self.summary_table.setRowCount(0)
        if summary_df is None or summary_df.empty:
            return
        for row_idx, (_, row) in enumerate(summary_df.iterrows()):
            self.summary_table.insertRow(row_idx)
            self.summary_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(row["start"])))
            self.summary_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(row["end"])))
            mean = row.get("mean")
            rel = row.get("relative_to_threshold")
            pct = row.get("time_above_pct")
            auc = row.get("auc")
            self.summary_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(self._fmt_float(mean)))
            self.summary_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(self._fmt_ratio(rel)))
            self.summary_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(self._fmt_percent(pct)))
            self.summary_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(self._fmt_float(auc)))

    def set_time_range(self, start, end):
        if start is None or end is None:
            self.range_label.setText("Time window: full data")
        else:
            self.range_label.setText(f"Time window: {start} → {end}")

    def _set_header_tooltips(self):
        tips = {
            2: "Average level across the period (time-weighted mean).",
            3: "Average level divided by the threshold. 1.0x means equal to threshold.",
            4: "Percent of time above the threshold.",
            5: "Raw total exposure (value × seconds).",
        }
        header = self.summary_table.horizontalHeader()
        for col, tip in tips.items():
            item = self.summary_table.horizontalHeaderItem(col)
            if item is not None:
                item.setToolTip(tip)
        header.setToolTip("Hover a column name for an explanation.")

    def _fmt_float(self, value):
        if value is None:
            return "n/a"
        if value != value:
            return "n/a"
        return f"{value:.2f}"

    def _fmt_ratio(self, value):
        if value is None or value != value:
            return "n/a"
        return f"{value:.2f}x"

    def _fmt_percent(self, value):
        if value is None or value != value:
            return "n/a"
        return f"{value:.1f}%"
