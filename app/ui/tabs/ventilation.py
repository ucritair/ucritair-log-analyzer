from __future__ import annotations

from PySide6 import QtWidgets, QtCore


class VentilationTab(QtWidgets.QWidget):
    fit_requested = QtCore.Signal(str, str, float, float, str, bool)
    detect_requested = QtCore.Signal(str, float, float, str, bool, float, float)
    annotate_requested = QtCore.Signal()
    clear_annotations_requested = QtCore.Signal()

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Estimate air change rate by fitting a decay curve. "
            "Use a time window in the Plot tab if you want to limit the data."
        )
        intro.setWordWrap(True)
        intro.setObjectName("introText")
        layout.addWidget(intro)

        self.kind_combo = QtWidgets.QComboBox()
        self.kind_combo.addItem("Carbon dioxide (CO2)", "co2")
        self.kind_combo.addItem("Particle count (PN10)", "pn10")
        self.kind_combo.setToolTip("Choose which measurement to use for the decay fit.")

        self.method_combo = QtWidgets.QComboBox()
        self.method_combo.setToolTip("Choose how the decay is fitted.")
        self._method_options = {
            "co2": [
                ("Regression (recommended)", "regression"),
                ("Two-point estimate", "two_point"),
                ("Time to 63% drop (1/e)", "time_constant_63"),
            ],
            "pn10": [
                ("Nonlinear fit (recommended)", "nonlinear"),
                ("Log-linear fit", "log_linear"),
            ],
        }

        self.baseline_mode = QtWidgets.QComboBox()
        self.baseline_mode.addItem("Manual value", "manual")
        self.baseline_mode.addItem("Use 430 ppm", "drop_430")
        self.baseline_mode.addItem("Low percentile (P5)", "percentile")
        self.baseline_mode.setToolTip("Choose how the baseline level is chosen.")
        self.baseline_input = QtWidgets.QLineEdit("430")
        self.baseline_input.setToolTip("Manual baseline value (ppm).")
        self.percentile_input = QtWidgets.QLineEdit("5")
        self.percentile_input.setToolTip("Percentile for baseline (e.g., 5 for P5).")
        self.selection_only = QtWidgets.QCheckBox("Use selected time window only")
        self.selection_only.setToolTip("Use the time window from the Plot tab.")
        self.range_label = QtWidgets.QLabel("Time window: full data")
        self.fit_btn = QtWidgets.QPushButton("Compute air change rate")
        self.fit_btn.setToolTip("Fit a decay curve and compute ACH/eACH.")
        self.fit_btn.setObjectName("primaryButton")
        self.result = QtWidgets.QLabel("No result yet.")
        self.warnings = QtWidgets.QLabel("")

        fit_group = QtWidgets.QGroupBox("Single fit")
        fit_form = QtWidgets.QFormLayout(fit_group)
        fit_form.addRow("Use data from", self.kind_combo)
        fit_form.addRow("Fit method", self.method_combo)
        fit_form.addRow("Baseline reference", self.baseline_mode)
        fit_form.addRow("Baseline value", self.baseline_input)
        fit_form.addRow("Percentile", self.percentile_input)
        fit_form.addRow(self.selection_only)
        fit_form.addRow(self.range_label)
        fit_form.addRow(self.fit_btn)
        fit_form.addRow(self.result)
        fit_form.addRow(self.warnings)
        layout.addWidget(fit_group)

        events_group = QtWidgets.QGroupBox("Find decay events")
        events_form = QtWidgets.QFormLayout(events_group)
        self.min_drop_input = QtWidgets.QLineEdit("300")
        self.min_drop_input.setToolTip("Minimum drop required for a decay event (ppm).")
        self.min_minutes_input = QtWidgets.QLineEdit("10")
        self.min_minutes_input.setToolTip("Minimum duration for a decay event (minutes).")
        self.detect_btn = QtWidgets.QPushButton("Find decay events")
        self.detect_btn.setToolTip("Scan the CO2 series and find decay events.")
        self.annotate_btn = QtWidgets.QPushButton("Annotate events on plot")
        self.annotate_btn.setToolTip("Draw event markers on the plot for the detected events.")
        self.clear_annotations_btn = QtWidgets.QPushButton("Clear plot annotations")
        self.clear_annotations_btn.setToolTip("Remove event markers from the plot.")
        self.events_note = QtWidgets.QLabel("Event detection currently uses CO2 only.")
        self.events_note.setWordWrap(True)
        self.events_table = QtWidgets.QTableWidget(0, 7)
        self.events_table.setHorizontalHeaderLabels(
            ["Label", "Start", "End", "Peak", "Air change rate", "Fit quality (R^2)", "Warnings"]
        )
        self.events_table.horizontalHeader().setStretchLastSection(True)
        self.events_table.verticalHeader().setVisible(False)
        self.summary_label = QtWidgets.QLabel("Summary (good fits only): none")

        events_form.addRow(self.events_note)
        events_form.addRow("Minimum drop (ppm)", self.min_drop_input)
        events_form.addRow("Minimum duration (min)", self.min_minutes_input)
        events_form.addRow(self.detect_btn)
        events_form.addRow(self.annotate_btn)
        events_form.addRow(self.clear_annotations_btn)
        events_form.addRow(self.events_table)
        events_form.addRow(self.summary_label)
        layout.addWidget(events_group)

        self.kind_combo.currentIndexChanged.connect(self._sync_method_options)
        self.baseline_mode.currentIndexChanged.connect(self._sync_baseline_controls)
        self.fit_btn.clicked.connect(self._emit_fit)
        self.detect_btn.clicked.connect(self._emit_detect)
        self.annotate_btn.clicked.connect(self.annotate_requested.emit)
        self.clear_annotations_btn.clicked.connect(self.clear_annotations_requested.emit)

        self._sync_method_options()
        self._sync_baseline_controls()

    def _emit_fit(self):
        kind = self.kind_combo.currentData() or self.kind_combo.currentText()
        method = self.method_combo.currentData() or self.method_combo.currentText()
        try:
            baseline = float(self.baseline_input.text())
        except ValueError:
            baseline = 0.0
        try:
            percentile = float(self.percentile_input.text())
        except ValueError:
            percentile = 5.0
        baseline_mode = self.baseline_mode.currentData() or self.baseline_mode.currentText()
        selection_only = self.selection_only.isChecked()
        self.fit_requested.emit(kind, baseline_mode, baseline, percentile, method, selection_only)

    def _emit_detect(self):
        baseline_mode = self.baseline_mode.currentData() or self.baseline_mode.currentText()
        try:
            baseline = float(self.baseline_input.text())
        except ValueError:
            baseline = 0.0
        try:
            percentile = float(self.percentile_input.text())
        except ValueError:
            percentile = 5.0
        try:
            min_drop = float(self.min_drop_input.text())
        except ValueError:
            min_drop = 100.0
        try:
            min_minutes = float(self.min_minutes_input.text())
        except ValueError:
            min_minutes = 10.0
        method = self.method_combo.currentData() or self.method_combo.currentText()
        selection_only = self.selection_only.isChecked()
        self.detect_requested.emit(baseline_mode, baseline, percentile, method, selection_only, min_drop, min_minutes)

    def set_dataset(self, dataset):
        pass

    def set_time_range(self, start, end):
        if start is None or end is None:
            self.range_label.setText("Time window: full data")
        else:
            self.range_label.setText(f"Time window: {start} → {end}")

    def show_result(self, result):
        self.result.setText(f"Air change rate: {result.ach:.2f} per hour | Fit quality (R^2): {result.r2:.2f}")
        if result.warnings:
            self.warnings.setText("Warnings: " + ", ".join(result.warnings))
        else:
            self.warnings.setText("")

    def show_events(self, events):
        self.events_table.setRowCount(0)
        for row_idx, event in enumerate(events):
            self.events_table.insertRow(row_idx)
            self.events_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(event.label))
            self.events_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(event.start)))
            self.events_table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(event.end)))
            self.events_table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(f"{event.peak_value:.1f}"))
            self.events_table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(f"{event.ach:.2f}"))
            self.events_table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(f"{event.r2:.2f}"))
            self.events_table.setItem(row_idx, 6, QtWidgets.QTableWidgetItem(", ".join(event.warnings)))

    def show_stats(self, stats: dict):
        if not stats:
            self.summary_label.setText("Summary (good fits only): none")
            return
        text = (
            f"Summary (R^2>=0.9): n={stats['n']} | "
            f"mean={stats['mean']:.2f} | median={stats['median']:.2f} | "
            f"min={stats['min']:.2f} | max={stats['max']:.2f} | "
            f"std={stats['std']:.2f}"
        )
        self.summary_label.setText(text)

    def _sync_method_options(self):
        kind = self.kind_combo.currentData() or "co2"
        self.method_combo.blockSignals(True)
        self.method_combo.clear()
        for label, value in self._method_options.get(kind, []):
            self.method_combo.addItem(label, value)
        self.method_combo.blockSignals(False)
        co2_mode = kind == "co2"
        self.min_drop_input.setEnabled(co2_mode)
        self.min_minutes_input.setEnabled(co2_mode)
        self.detect_btn.setEnabled(co2_mode)
        self.annotate_btn.setEnabled(co2_mode)
        self.clear_annotations_btn.setEnabled(co2_mode)
        self.events_note.setVisible(co2_mode is False)

    def _sync_baseline_controls(self):
        mode = self.baseline_mode.currentData() or "manual"
        self.baseline_input.setEnabled(mode == "manual")
        self.percentile_input.setEnabled(mode == "percentile")
        if mode == "drop_430":
            self.baseline_input.setText("430")
        elif mode == "percentile":
            self.baseline_input.setText("")
