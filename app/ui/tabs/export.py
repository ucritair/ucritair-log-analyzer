from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets, QtCore


class ExportTab(QtWidgets.QWidget):
    export_csv_requested = QtCore.Signal(Path)
    export_parquet_requested = QtCore.Signal(Path)
    export_filtered_csv_requested = QtCore.Signal(Path)
    export_aqi_requested = QtCore.Signal(Path)
    export_ventilation_requested = QtCore.Signal(Path)
    export_exposure_requested = QtCore.Signal(Path)
    export_plot_requested = QtCore.Signal(Path)

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "Export cleaned data, analysis results, or a plot image for sharing."
        )
        intro.setWordWrap(True)
        intro.setObjectName("introText")
        layout.addWidget(intro)

        self.export_csv_btn = QtWidgets.QPushButton("Export Clean CSV")
        self.export_csv_btn.setToolTip("Save the cleaned dataset as CSV.")
        self.export_parquet_btn = QtWidgets.QPushButton("Export Clean Parquet")
        self.export_parquet_btn.setToolTip("Save the cleaned dataset as Parquet.")
        self.export_filtered_btn = QtWidgets.QPushButton("Export Filtered CSV")
        self.export_filtered_btn.setToolTip("Save the filtered series as CSV.")
        self.export_aqi_btn = QtWidgets.QPushButton("Export air quality index (CSV)")
        self.export_aqi_btn.setToolTip("Save the computed air quality index as CSV.")
        self.export_vent_btn = QtWidgets.QPushButton("Export ventilation result (JSON)")
        self.export_vent_btn.setToolTip("Save the latest ventilation fit result.")
        self.export_exposure_btn = QtWidgets.QPushButton("Export Exposure CSV")
        self.export_exposure_btn.setToolTip("Save the exposure summary as CSV.")
        self.export_plot_btn = QtWidgets.QPushButton("Export Plot Image")
        self.export_plot_btn.setToolTip("Save the current plot as an image.")
        self.export_plot_btn.setObjectName("primaryButton")

        data_group = QtWidgets.QGroupBox("Data exports")
        data_layout = QtWidgets.QVBoxLayout(data_group)
        data_layout.addWidget(self.export_csv_btn)
        data_layout.addWidget(self.export_parquet_btn)
        data_layout.addWidget(self.export_filtered_btn)

        analysis_group = QtWidgets.QGroupBox("Analysis exports")
        analysis_layout = QtWidgets.QVBoxLayout(analysis_group)
        analysis_layout.addWidget(self.export_aqi_btn)
        analysis_layout.addWidget(self.export_vent_btn)
        analysis_layout.addWidget(self.export_exposure_btn)

        plot_group = QtWidgets.QGroupBox("Plot export")
        plot_layout = QtWidgets.QVBoxLayout(plot_group)
        plot_layout.addWidget(self.export_plot_btn)

        layout.addWidget(data_group)
        layout.addWidget(analysis_group)
        layout.addWidget(plot_group)
        layout.addStretch(1)

        self.export_csv_btn.clicked.connect(self._emit_csv)
        self.export_parquet_btn.clicked.connect(self._emit_parquet)
        self.export_filtered_btn.clicked.connect(self._emit_filtered)
        self.export_aqi_btn.clicked.connect(self._emit_aqi)
        self.export_vent_btn.clicked.connect(self._emit_vent)
        self.export_exposure_btn.clicked.connect(self._emit_exposure)
        self.export_plot_btn.clicked.connect(self._emit_plot)

    def set_dataset(self, dataset):
        pass

    def _emit_csv(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Clean CSV", "clean.csv", "CSV Files (*.csv)")
        if path:
            self.export_csv_requested.emit(Path(path))

    def _emit_parquet(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Clean Parquet", "clean.parquet", "Parquet Files (*.parquet)")
        if path:
            self.export_parquet_requested.emit(Path(path))

    def _emit_filtered(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Filtered CSV", "filtered.csv", "CSV Files (*.csv)")
        if path:
            self.export_filtered_csv_requested.emit(Path(path))

    def _emit_aqi(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export air quality index (CSV)", "aqi.csv", "CSV Files (*.csv)"
        )
        if path:
            self.export_aqi_requested.emit(Path(path))

    def _emit_vent(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export ventilation result (JSON)", "ventilation.json", "JSON Files (*.json)"
        )
        if path:
            self.export_ventilation_requested.emit(Path(path))

    def _emit_exposure(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Exposure CSV", "exposure.csv", "CSV Files (*.csv)")
        if path:
            self.export_exposure_requested.emit(Path(path))

    def _emit_plot(self):
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Export Plot", "plot.png", "PNG Files (*.png)")
        if path:
            self.export_plot_requested.emit(Path(path))
