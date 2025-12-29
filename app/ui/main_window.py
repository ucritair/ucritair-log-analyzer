from __future__ import annotations

from pathlib import Path
from typing import Dict
import json
import pandas as pd
from PySide6 import QtWidgets, QtCore, QtGui

from app.core.state import AppState
from app.data.importer import DatasetImporter
from app.data.mask_rules import apply_validity_masks
from app.data.gaps import detect_gaps
from app.diagnostics.flatline import FlatlineConfig, flag_flatlines
from app.persistence.cache import cache_filtered
from app.persistence.project import Project, save_project, load_project
from app.analysis.aqi import load_standard_pack, compute_aqi, apply_averaging
from app.analysis.ventilation import fit_co2_decay, fit_pn_decay, detect_co2_decay_events, summarize_ach
from app.analysis.exposure import exposure_stats, summarize_periods
from app.ui.tabs.import_clean import ImportCleanTab
from app.ui.tabs.plot import PlotTab
from app.ui.tabs.filters import FiltersTab
from app.ui.tabs.aqi import AqiTab
from app.ui.tabs.ventilation import VentilationTab
from app.ui.tabs.exposure import ExposureTab
from app.ui.tabs.export import ExportTab
from app.ui.tabs.diagnostics import DiagnosticsTab
from app.ui.tabs.data_table import DataTableTab
from app.ui.metric_catalog import (
    metric_display_name,
    metric_tooltip,
    metric_group,
    sorted_metric_keys,
    GROUP_ORDER,
)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, state: AppState):
        super().__init__()
        self.state = state
        self.importer = DatasetImporter()
        self.last_vent_result = None
        self.last_exposure_summary = None
        self.decay_events = []

        self.setWindowTitle("μCritAir Log Analyzer")
        icon_path = Path(__file__).resolve().parents[1] / "resources" / "icons" / "ucritter.png"
        if icon_path.exists():
            self.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self._build_menu()
        self._build_ui()
        self._connect_signals()

    def _build_menu(self):
        menu = self.menuBar()
        file_menu = menu.addMenu("File")

        import_action = QtGui.QAction("Import data (CSV)", self)
        save_project_action = QtGui.QAction("Save project", self)
        load_project_action = QtGui.QAction("Load project", self)
        exit_action = QtGui.QAction("Quit", self)
        import_action.setStatusTip("Open a CSV log file.")
        save_project_action.setStatusTip("Save the current session.")
        load_project_action.setStatusTip("Open a saved session.")
        exit_action.setStatusTip("Close the application.")

        import_action.triggered.connect(self._import_csv)
        save_project_action.triggered.connect(self._save_project)
        load_project_action.triggered.connect(self._load_project)
        exit_action.triggered.connect(self.close)

        file_menu.addAction(import_action)
        file_menu.addSeparator()
        file_menu.addAction(save_project_action)
        file_menu.addAction(load_project_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)

        layout = QtWidgets.QHBoxLayout(central)

        # Left panel
        left_panel = QtWidgets.QWidget()
        left_panel.setObjectName("sidebar")
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)
        left_layout.setSpacing(8)

        self.workflow_label = QtWidgets.QLabel(
            "<b>Start here</b><br>"
            "1. Import a log file<br>"
            "2. Choose what to show<br>"
            "3. Explore in Plot<br>"
            "4. Run analyses in other tabs<br>"
            "5. Export results"
        )
        self.workflow_label.setWordWrap(True)
        self.workflow_label.setToolTip("Quick steps to get from raw data to plots and results.")
        self.workflow_label.setObjectName("sidebarIntro")
        left_layout.addWidget(self.workflow_label)

        data_group = QtWidgets.QGroupBox("Data")
        data_layout = QtWidgets.QVBoxLayout(data_group)
        self.import_btn = QtWidgets.QPushButton("Import CSV")
        self.import_btn.setObjectName("primaryButton")
        self.import_btn.setToolTip("Open a CSV log file from disk.")
        self.dataset_list = QtWidgets.QListWidget()
        self.dataset_list.setToolTip("Pick which file to view and analyze.")
        data_layout.addWidget(self.import_btn)
        data_layout.addWidget(QtWidgets.QLabel("Loaded logs"))
        data_layout.addWidget(self.dataset_list)
        left_layout.addWidget(data_group)

        metrics_group = QtWidgets.QGroupBox("Metrics")
        metrics_layout = QtWidgets.QVBoxLayout(metrics_group)
        metrics_note = QtWidgets.QLabel("Each metric uses its own scale.")
        metrics_note.setWordWrap(True)
        metrics_note.setToolTip("This keeps different units on separate scales.")
        self.metric_tree = QtWidgets.QTreeWidget()
        self.metric_tree.setHeaderHidden(True)
        self.metric_tree.setRootIsDecorated(False)
        self.metric_tree.setAlternatingRowColors(True)
        self.metric_tree.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.metric_tree.setUniformRowHeights(True)
        self.metric_tree.setToolTip("Check the boxes to show a metric in the plot.")
        button_row = QtWidgets.QHBoxLayout()
        self.metric_select_all_btn = QtWidgets.QPushButton("Select all")
        self.metric_clear_btn = QtWidgets.QPushButton("Clear selection")
        self.metric_select_all_btn.setToolTip("Show every metric that is available.")
        self.metric_clear_btn.setToolTip("Hide all metrics from the plot.")
        button_row.addWidget(self.metric_select_all_btn)
        button_row.addWidget(self.metric_clear_btn)
        button_row.addStretch(1)
        metrics_layout.addWidget(metrics_note)
        metrics_layout.addWidget(self.metric_tree)
        metrics_layout.addLayout(button_row)
        left_layout.addWidget(metrics_group)
        left_layout.addStretch(1)

        # Right panel with tabs
        self.tabs = QtWidgets.QTabWidget()
        self.import_tab = ImportCleanTab(self.state)
        self.plot_tab = PlotTab()
        self.filters_tab = FiltersTab(self.state)
        self.aqi_tab = AqiTab()
        self.vent_tab = VentilationTab()
        self.exposure_tab = ExposureTab()
        self.export_tab = ExportTab()
        self.data_tab = DataTableTab()
        self.diag_tab = DiagnosticsTab()

        self.tabs.addTab(self.import_tab, "Import")
        self.tabs.addTab(self.plot_tab, "Plot")
        self.tabs.addTab(self.filters_tab, "Smoothing")
        self.tabs.addTab(self.aqi_tab, "Air Quality (AQI)")
        self.tabs.addTab(self.vent_tab, "Ventilation (ACH)")
        self.tabs.addTab(self.exposure_tab, "Exposure")
        self.tabs.addTab(self.export_tab, "Export")
        self.tabs.addTab(self.data_tab, "Data Table")
        self.tabs.addTab(self.diag_tab, "Data checks")

        self.tabs.setTabToolTip(0, "Import files and choose cleaning options.")
        self.tabs.setTabToolTip(1, "Explore the selected metrics over time.")
        self.tabs.setTabToolTip(2, "Apply smoothing to reduce noise.")
        self.tabs.setTabToolTip(3, "Compute the air quality index from particles.")
        self.tabs.setTabToolTip(4, "Estimate air change rate from decay curves.")
        self.tabs.setTabToolTip(5, "Summarize exposure over time.")
        self.tabs.setTabToolTip(6, "Export data, results, or plots.")
        self.tabs.setTabToolTip(7, "Browse the data table.")
        self.tabs.setTabToolTip(8, "Inspect gaps, flatlines, and masked values.")
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setExpanding(False)

        splitter = QtWidgets.QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(1, 1)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        left_panel.setMinimumWidth(280)
        left_panel.setMaximumWidth(360)
        layout.addWidget(splitter)

        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def _connect_signals(self):
        self.import_btn.clicked.connect(self._import_csv)
        self.dataset_list.currentRowChanged.connect(self._on_dataset_selected)
        self.metric_tree.itemChanged.connect(self._on_metric_tree_changed)
        self.metric_select_all_btn.clicked.connect(lambda: self._set_all_metrics(True))
        self.metric_clear_btn.clicked.connect(lambda: self._set_all_metrics(False))
        self.import_tab.config_changed.connect(self._on_processing_config_changed)
        self.filters_tab.filters_changed.connect(self._on_filters_changed)
        self.aqi_tab.compute_requested.connect(self._on_compute_aqi)
        self.vent_tab.fit_requested.connect(self._on_fit_decay)
        self.vent_tab.detect_requested.connect(self._on_detect_decays)
        self.vent_tab.annotate_requested.connect(self._on_annotate_decays)
        self.vent_tab.clear_annotations_requested.connect(self._on_clear_decay_annotations)
        self.exposure_tab.compute_requested.connect(self._on_exposure_compute)
        self.export_tab.export_csv_requested.connect(self._on_export_csv)
        self.export_tab.export_parquet_requested.connect(self._on_export_parquet)
        self.export_tab.export_filtered_csv_requested.connect(self._on_export_filtered_csv)
        self.export_tab.export_aqi_requested.connect(self._on_export_aqi)
        self.export_tab.export_ventilation_requested.connect(self._on_export_ventilation)
        self.export_tab.export_exposure_requested.connect(self._on_export_exposure)
        self.export_tab.export_plot_requested.connect(self._on_export_plot)
        self.plot_tab.time_range_changed.connect(self._on_time_range_changed)

    def _import_csv(self):
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import data (CSV)", str(Path.home()), "CSV Files (*.csv *.CSV)"
        )
        if not file_path:
            return
        try:
            dataset = self.importer.load_csv(Path(file_path), self.state.processing_config)
        except Exception as exc:
            QtWidgets.QMessageBox.critical(self, "Import Error", str(exc))
            return

        self.state.datasets.append(dataset)
        self.dataset_list.addItem(dataset.name)
        self.dataset_list.setCurrentRow(len(self.state.datasets) - 1)
        self.status_bar.showMessage(f"Loaded {dataset.name}")

    def _save_project(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Project", "project.json", "JSON Files (*.json)")
        if not path:
            return
        dataset_paths = [d.metadata.get("path") for d in self.state.datasets if d.metadata.get("path")]
        project = Project(
            dataset_paths=dataset_paths,
            processing_config=self.state.processing_config,
            filter_config=self.state.filter_config,
            active_standard_pack=self.state.active_standard_pack,
            active_dataset_index=self.dataset_list.currentRow(),
        )
        save_project(project, Path(path))

    def _load_project(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Load Project", str(Path.home()), "JSON Files (*.json)")
        if not path:
            return
        project = load_project(Path(path))

        self.state.processing_config = project.processing_config
        self.state.filter_config = project.filter_config
        self.state.active_standard_pack = project.active_standard_pack

        self.state.datasets.clear()
        self.dataset_list.clear()
        for dataset_path in project.dataset_paths:
            try:
                dataset = self.importer.load_csv(Path(dataset_path), self.state.processing_config)
                self.state.datasets.append(dataset)
                self.dataset_list.addItem(dataset.name)
            except Exception:
                continue

        if self.state.datasets:
            index = max(0, min(project.active_dataset_index, len(self.state.datasets) - 1))
            self.dataset_list.setCurrentRow(index)

        self.filters_tab.set_config(self.state.filter_config)
        self.import_tab.set_dataset(self._current_dataset())

    def _on_dataset_selected(self, idx: int):
        if idx < 0 or idx >= len(self.state.datasets):
            return
        dataset = self.state.datasets[idx]
        self.decay_events = []
        self.plot_tab.set_decay_events([])
        self._populate_metrics(dataset)
        self._refresh_plot()
        self.import_tab.set_dataset(dataset)
        self.aqi_tab.set_dataset(dataset)
        self.vent_tab.set_dataset(dataset)
        self.exposure_tab.set_dataset(dataset)
        self.export_tab.set_dataset(dataset)
        self.data_tab.set_dataset(dataset)
        self.diag_tab.set_dataset(dataset)
        self.status_bar.showMessage(f"Viewing {dataset.name} ({len(dataset.clean)} rows)")

    def _populate_metrics(self, dataset, selected_keys: set[str] | None = None):
        self.metric_tree.blockSignals(True)
        self.metric_tree.clear()
        metrics = [c for c in self._active_clean_df(dataset).columns if c != "timestamp"]
        ordered_keys = sorted_metric_keys(metrics)

        grouped: dict[str, list[str]] = {}
        for key in ordered_keys:
            grouped.setdefault(metric_group(key), []).append(key)

        for group in GROUP_ORDER:
            keys = grouped.get(group, [])
            if not keys:
                continue
            group_item = QtWidgets.QTreeWidgetItem(self.metric_tree)
            group_item.setText(0, group)
            group_item.setFlags(
                group_item.flags()
                | QtCore.Qt.ItemFlag.ItemIsAutoTristate
                | QtCore.Qt.ItemIsUserCheckable
            )
            group_item.setCheckState(0, QtCore.Qt.Unchecked)
            group_item.setExpanded(True)
            for key in keys:
                item = QtWidgets.QTreeWidgetItem(group_item)
                item.setText(0, metric_display_name(key))
                item.setData(0, QtCore.Qt.UserRole, key)
                if selected_keys and key in selected_keys:
                    item.setCheckState(0, QtCore.Qt.Checked)
                else:
                    item.setCheckState(0, QtCore.Qt.Unchecked)
                item.setToolTip(0, metric_tooltip(key))

        self.metric_tree.blockSignals(False)

    def _on_metric_tree_changed(self, item: QtWidgets.QTreeWidgetItem, column: int):
        self._refresh_plot()

    def _set_all_metrics(self, checked: bool):
        self.metric_tree.blockSignals(True)
        root = self.metric_tree.invisibleRootItem()
        state = QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked
        for i in range(root.childCount()):
            group_item = root.child(i)
            group_item.setCheckState(0, state)
        self.metric_tree.blockSignals(False)
        self._refresh_plot()

    def _selected_metric_keys(self) -> list[str]:
        keys: list[str] = []
        root = self.metric_tree.invisibleRootItem()
        for i in range(root.childCount()):
            group_item = root.child(i)
            for j in range(group_item.childCount()):
                item = group_item.child(j)
                if item.checkState(0) == QtCore.Qt.Checked:
                    key = item.data(0, QtCore.Qt.UserRole)
                    if key:
                        keys.append(str(key))
        return keys

    def _collect_selected_series(self) -> Dict[str, pd.Series]:
        dataset = self._current_dataset()
        if dataset is None:
            return {}

        series_map: Dict[str, pd.Series] = {}
        filters_active = bool(self.state.filter_config.sma_window or self.state.filter_config.ema_tau)
        clean_df = self._active_clean_df(dataset)
        clean_indexed = clean_df.set_index("timestamp")
        filtered_df = None
        if filters_active:
            try:
                filtered_df = cache_filtered(clean_indexed, self.state.filter_config)
            except ValueError as exc:
                QtWidgets.QMessageBox.warning(self, "Smoothing error", str(exc))
                filters_active = False

        for metric in self._selected_metric_keys():
            if metric not in clean_indexed.columns:
                continue
            raw_series = clean_indexed[metric]
            if filters_active:
                filtered = filtered_df[metric] if filtered_df is not None else raw_series
                raw_name = f"{metric} (raw)"
                filt_name = f"{metric} (filtered)"
                series_map[raw_name] = raw_series
                series_map[filt_name] = filtered
            else:
                series_map[metric] = raw_series

        return series_map

    def _refresh_plot(self):
        series_map = self._collect_selected_series()
        self.plot_tab.plot_series(series_map)

    def _on_time_range_changed(self, start, end):
        if start is None or end is None:
            self.state.time_range = None
        else:
            self.state.time_range = (start, end)
        self.vent_tab.set_time_range(start, end)
        self.exposure_tab.set_time_range(start, end)
        self.data_tab.set_time_range(start, end)

    def _on_processing_config_changed(self):
        dataset = self._current_dataset()
        if dataset is None:
            return
        selected_metrics = set(self._selected_metric_keys())

        mask_result = apply_validity_masks(dataset.raw, self.state.processing_config)
        dataset.clean = mask_result.clean
        dataset.masks = mask_result.masks
        dataset.metadata["mask_reasons"] = mask_result.reasons
        dataset.metadata["gaps"] = detect_gaps(dataset.clean["timestamp"], self.state.processing_config.gap_factor)

        if self.state.processing_config.resample_interval:
            dataset.resampled = self.importer._resample(dataset.clean, self.state.processing_config.resample_interval)
            dataset.metadata["resample_interval"] = self.state.processing_config.resample_interval
            dataset.metadata["resampled_rows"] = int(dataset.resampled.shape[0])
        else:
            dataset.resampled = None
            dataset.metadata["resample_interval"] = None
            dataset.metadata["resampled_rows"] = None

        if self.state.processing_config.flatline_diag_enabled:
            flat_cfg = FlatlineConfig()
            flags = flag_flatlines(dataset.clean.set_index("timestamp"), flat_cfg)
            dataset.flags = flags
            if self.state.processing_config.flatline_automask:
                for col, mask in flags.items():
                    if col.startswith("pm") or col.startswith("pn"):
                        dataset.clean.loc[mask.values, col] = pd.NA
                        if col in dataset.masks:
                            dataset.masks[col] = dataset.masks[col] & ~mask.values
        else:
            dataset.flags = {}

        self._populate_metrics(dataset, selected_keys=selected_metrics)
        self._refresh_plot()
        self.data_tab.set_dataset(dataset)
        self.diag_tab.set_dataset(dataset)

    def _active_clean_df(self, dataset):
        if self.state.processing_config.use_resampled and dataset.resampled is not None:
            return dataset.resampled
        return dataset.clean

    def _on_filters_changed(self):
        self._refresh_plot()

    def _on_compute_aqi(self, pack_path: Path, averaging: str):
        dataset = self._current_dataset()
        if dataset is None:
            return
        pack = load_standard_pack(pack_path)
        df = self._active_clean_df(dataset).set_index("timestamp")
        pm25 = df.get("pm2_5")
        pm10 = df.get("pm10")
        if pm25 is not None:
            pm25 = apply_averaging(pm25, averaging)
        if pm10 is not None:
            pm10 = apply_averaging(pm10, averaging)
        aqi_df = compute_aqi(pm25, pm10, pack)
        self.aqi_tab.render_aqi(aqi_df, pack)

    def _on_fit_decay(
        self,
        kind: str,
        baseline_mode: str,
        baseline: float,
        percentile: float,
        method: str,
        selection_only: bool,
    ):
        dataset = self._current_dataset()
        if dataset is None:
            return
        df = self._active_clean_df(dataset)
        times = df["timestamp"]
        if selection_only and self.state.time_range:
            start, end = self.state.time_range
            mask = (times >= start) & (times <= end)
            df = df.loc[mask]
            times = df["timestamp"]

        baseline_value = baseline
        if baseline_mode == "drop_430":
            baseline_value = 430.0
        elif baseline_mode == "percentile":
            series_for_baseline = df.get("co2") if kind == "co2" else df.get("pn10_0")
            if series_for_baseline is not None and not series_for_baseline.dropna().empty:
                baseline_value = float(series_for_baseline.quantile(percentile / 100.0))
        if kind == "co2":
            series = df.get("co2")
            if series is None:
                QtWidgets.QMessageBox.warning(self, "Fit Error", "CO2 column not found")
                return
            if method not in ("regression", "two_point", "time_constant_63"):
                method = "regression"
            result = fit_co2_decay(times, series, baseline_value, method=method)
        else:
            series = df.get("pn10_0")
            if series is None:
                QtWidgets.QMessageBox.warning(self, "Fit Error", "PN10.0 column not found")
                return
            if method not in ("nonlinear", "log_linear"):
                method = "nonlinear"
            result = fit_pn_decay(times, series, baseline_value, method=method)
        self.last_vent_result = result
        self.vent_tab.show_result(result)

    def _on_detect_decays(
        self,
        baseline_mode: str,
        baseline: float,
        percentile: float,
        method: str,
        selection_only: bool,
        min_drop: float,
        min_minutes: float,
    ):
        dataset = self._current_dataset()
        if dataset is None:
            return
        df = self._active_clean_df(dataset)
        times = df["timestamp"]
        if selection_only and self.state.time_range:
            start, end = self.state.time_range
            mask = (times >= start) & (times <= end)
            df = df.loc[mask]
            times = df["timestamp"]

        series = df.get("co2")
        if series is None:
            QtWidgets.QMessageBox.warning(self, "Detect Error", "CO2 column not found")
            return

        baseline_value = baseline
        if baseline_mode == "drop_430":
            baseline_value = 430.0
        elif baseline_mode == "percentile":
            if not series.dropna().empty:
                baseline_value = float(series.quantile(percentile / 100.0))

        if method not in ("regression", "two_point", "time_constant_63"):
            method = "time_constant_63"

        events = detect_co2_decay_events(
            times,
            series,
            baseline_value,
            min_drop=min_drop,
            min_minutes=min_minutes,
            method=method,
        )
        self.decay_events = events
        self.vent_tab.show_events(events)
        self.vent_tab.show_stats(summarize_ach(events, min_r2=0.9))
        self.plot_tab.set_decay_events(events)

    def _on_annotate_decays(self):
        self.plot_tab.set_decay_events(self.decay_events)

    def _on_clear_decay_annotations(self):
        self.plot_tab.set_decay_events([])

    def _on_exposure_compute(self, metric: str, threshold: float, freq_label: str, selection_only: bool):
        dataset = self._current_dataset()
        if dataset is None:
            return
        series = self._active_clean_df(dataset).set_index("timestamp")[metric]
        series = self._apply_time_range(series, selection_only)
        stats = exposure_stats(series, threshold)
        self.exposure_tab.show_result(stats, threshold)

        freq_map = {"daily": "D", "weekly": "W", "monthly": "M"}
        freq = freq_map.get(freq_label, "D")
        try:
            summary = summarize_periods(series, threshold, freq)
        except Exception:
            summary = None
        self.last_exposure_summary = summary
        self.exposure_tab.show_summary(summary)

    def _on_export_csv(self, path: Path):
        dataset = self._current_dataset()
        if dataset is None:
            return
        dataset.clean.to_csv(path, index=False)

    def _on_export_parquet(self, path: Path):
        dataset = self._current_dataset()
        if dataset is None:
            return
        dataset.clean.to_parquet(path, index=False)

    def _on_export_filtered_csv(self, path: Path):
        dataset = self._current_dataset()
        if dataset is None:
            return
        df = self._active_clean_df(dataset).set_index("timestamp")
        if self.state.filter_config.sma_window or self.state.filter_config.ema_tau:
            filtered = cache_filtered(df, self.state.filter_config).reset_index()
        else:
            filtered = df.reset_index()
        filtered.to_csv(path, index=False)

    def _on_export_aqi(self, path: Path):
        dataset = self._current_dataset()
        if dataset is None:
            return
        pack_path = self.aqi_tab.pack_combo.currentData()
        if pack_path is None:
            return
        pack = load_standard_pack(pack_path)
        df = self._active_clean_df(dataset).set_index("timestamp")
        averaging = self.aqi_tab.averaging_combo.currentData() or self.aqi_tab.averaging_combo.currentText()
        pm25 = df.get("pm2_5")
        pm10 = df.get("pm10")
        if pm25 is not None:
            pm25 = apply_averaging(pm25, averaging)
        if pm10 is not None:
            pm10 = apply_averaging(pm10, averaging)
        aqi_df = compute_aqi(pm25, pm10, pack)
        aqi_df.to_csv(path, index=True)

    def _on_export_ventilation(self, path: Path):
        if self.last_vent_result is None:
            QtWidgets.QMessageBox.information(self, "Export", "No ventilation result to export")
            return
        payload = {
            "k_per_hr": self.last_vent_result.k_per_hr,
            "ach": self.last_vent_result.ach,
            "baseline": self.last_vent_result.baseline,
            "r2": self.last_vent_result.r2,
            "warnings": self.last_vent_result.warnings,
        }
        path.write_text(json.dumps(payload, indent=2))

    def _on_export_exposure(self, path: Path):
        if self.last_exposure_summary is None or getattr(self.last_exposure_summary, "empty", True):
            QtWidgets.QMessageBox.information(self, "Export", "No exposure summary to export")
            return
        self.last_exposure_summary.to_csv(path, index=False)

    def _on_export_plot(self, path: Path):
        self.plot_tab.export_plot(path)

    def _current_dataset(self):
        idx = self.dataset_list.currentRow()
        if idx < 0 or idx >= len(self.state.datasets):
            return None
        return self.state.datasets[idx]

    def _apply_time_range(self, series: pd.Series, selection_only: bool) -> pd.Series:
        if not selection_only:
            return series
        if self.state.time_range is None:
            return series
        start, end = self.state.time_range
        return series.loc[start:end]
