from __future__ import annotations

from pathlib import Path
from PySide6 import QtWidgets, QtCore
import pandas as pd
import pyqtgraph as pg

from app.analysis.aqi import aqi_summary, load_standard_pack


class AqiTab(QtWidgets.QWidget):
    compute_requested = QtCore.Signal(Path, str)

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QtWidgets.QLabel(
            "This tab calculates an air quality index using PM2.5 and PM10 only."
        )
        intro.setWordWrap(True)
        intro.setObjectName("introText")
        layout.addWidget(intro)

        self.pack_combo = QtWidgets.QComboBox()
        self.pack_combo.setToolTip("Choose the standard used to compute the air quality index.")
        self.averaging_combo = QtWidgets.QComboBox()
        self.averaging_combo.addItem("Instant (no averaging)", "instant")
        self.averaging_combo.addItem("Rolling 24-hour average", "rolling_24h")
        self.averaging_combo.addItem("Daily average", "daily")
        self.averaging_combo.setToolTip("How concentrations are averaged before AQI is computed.")
        self.shading_checkbox = QtWidgets.QCheckBox("Show category colors on the plot")
        self.shading_checkbox.setChecked(True)
        self.shading_checkbox.setToolTip("Adds colored background bands for the AQI categories.")
        self.compute_btn = QtWidgets.QPushButton("Compute air quality index")
        self.compute_btn.setToolTip("Run the AQI calculation with the settings above.")
        self.compute_btn.setObjectName("primaryButton")
        self.summary = QtWidgets.QLabel("No air quality index computed")

        axis = pg.DateAxisItem(orientation="bottom")
        self.plot_widget = pg.PlotWidget(axisItems={"bottom": axis})

        self.summary_table = QtWidgets.QTableWidget(0, 2)
        self.summary_table.setHorizontalHeaderLabels(["Metric", "Value"])
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.verticalHeader().setVisible(False)

        controls_group = QtWidgets.QGroupBox("AQI settings")
        controls = QtWidgets.QFormLayout(controls_group)
        controls.addRow("Standard", self.pack_combo)
        controls.addRow("Averaging", self.averaging_combo)
        controls.addRow(self.shading_checkbox)
        controls.addRow(self.compute_btn)
        layout.addWidget(controls_group)
        layout.addWidget(self.summary)
        layout.addWidget(self.plot_widget)
        layout.addWidget(self.summary_table)

        self.compute_btn.clicked.connect(self._emit_compute)
        self._load_packs()
        self.shading_checkbox.toggled.connect(self._replot)

        self.last_aqi = None
        self.last_pack = None
        self._category_regions = []

    def _load_packs(self):
        base = Path(__file__).resolve().parents[2] / "resources" / "standards"
        self.pack_combo.clear()
        for path in base.glob("*.yaml"):
            try:
                pack = load_standard_pack(path)
                label = pack.name
            except Exception:
                label = path.stem
            self.pack_combo.addItem(label, userData=path)

    def _emit_compute(self):
        path = self.pack_combo.currentData()
        if path:
            averaging = self.averaging_combo.currentData() or self.averaging_combo.currentText()
            self.compute_requested.emit(path, averaging)

    def set_dataset(self, dataset):
        pass

    def render_aqi(self, aqi_df: pd.DataFrame, pack):
        self.last_aqi = aqi_df
        self.last_pack = pack
        self.plot_widget.clear()
        self._category_regions = []

        if aqi_df.empty:
            self.summary.setText("No air quality values")
            self.summary_table.setRowCount(0)
            return

        if isinstance(aqi_df.index, pd.DatetimeIndex):
            x = aqi_df.index.view("int64") / 1e9
        else:
            x = aqi_df.index.to_numpy(dtype=float)
        y = aqi_df["aqi_overall"].to_numpy(dtype=float)

        if pack.categories and self.shading_checkbox.isChecked():
            for cat in pack.categories:
                color = cat.get("color", "#CCCCCC")
                qcolor = pg.mkColor(color)
                qcolor.setAlpha(60)
                region = pg.LinearRegionItem(
                    values=(cat["low"], cat["high"]),
                    orientation=pg.LinearRegionItem.Horizontal,
                    brush=pg.mkBrush(qcolor),
                    movable=False,
                )
                self.plot_widget.addItem(region)
                self._category_regions.append(region)

        self.plot_widget.plot(x=x, y=y, pen=pg.mkPen("#0072B2", width=2))

        self.summary.setText(f"{pack.name}: Max AQI {aqi_df['aqi_overall'].max():.0f}")
        summary = aqi_summary(aqi_df["aqi_overall"], pack.categories)
        self._render_summary(summary)

    def _replot(self):
        if self.last_aqi is None or self.last_pack is None:
            return
        self.render_aqi(self.last_aqi, self.last_pack)

    def _render_summary(self, summary: dict):
        self.summary_table.setRowCount(0)
        for row_idx, (key, value) in enumerate(summary.items()):
            self.summary_table.insertRow(row_idx)
            self.summary_table.setItem(row_idx, 0, QtWidgets.QTableWidgetItem(str(key)))
            self.summary_table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(value)))
