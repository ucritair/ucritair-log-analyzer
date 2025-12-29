from __future__ import annotations

from pathlib import Path
from typing import Dict, Callable
import pyqtgraph as pg
import pyqtgraph.exporters
import pandas as pd
from PySide6 import QtWidgets, QtCore, QtGui

from app.plot.plot_manager import PlotManager
from app.plot.palettes import OKABE_ITO
from app.ui.metric_catalog import metric_axis_label


class RangeViewBox(pg.ViewBox):
    def __init__(self, show_menu: Callable[[float], None]):
        super().__init__()
        self._show_menu = show_menu
        self._last_x = None

    def mouseClickEvent(self, ev):
        if ev.button() == QtCore.Qt.RightButton:
            ev.accept()
            self._last_x = self.mapSceneToView(ev.scenePos()).x()
            if self._last_x is not None:
                self._show_menu(self._last_x)
            return
        super().mouseClickEvent(ev)


class PlotTab(QtWidgets.QWidget):
    time_range_changed = QtCore.Signal(object, object)
    range_enabled_changed = QtCore.Signal(bool)

    def __init__(self):
        super().__init__()
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(8)

        intro = QtWidgets.QLabel(
            "Explore the selected metrics over time. Drag to pan or zoom, and use a time window for analyses."
        )
        intro.setWordWrap(True)
        intro.setObjectName("introText")
        layout.addWidget(intro)

        controls = QtWidgets.QHBoxLayout()
        self.range_checkbox = QtWidgets.QCheckBox("Use a time window for analyses")
        self.range_checkbox.setToolTip("When enabled, the selected window is used by Ventilation and Exposure.")
        self.clear_range_btn = QtWidgets.QPushButton("Clear time window")
        self.clear_range_btn.setToolTip("Clear the time window and show the full range.")
        self.clear_range_btn.setEnabled(False)
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["Pan (drag)", "Zoom (drag box)"])
        controls.addWidget(self.range_checkbox)
        controls.addWidget(self.clear_range_btn)
        controls.addStretch(1)
        controls.addWidget(QtWidgets.QLabel("Drag mode"))
        controls.addWidget(self.mode_combo)

        range_controls = QtWidgets.QHBoxLayout()
        self.start_edit = QtWidgets.QDateTimeEdit()
        self.end_edit = QtWidgets.QDateTimeEdit()
        for edit in (self.start_edit, self.end_edit):
            edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            edit.setCalendarPopup(True)
            edit.setTimeSpec(QtCore.Qt.UTC)
            edit.setToolTip("Use UTC times. Click to open the calendar picker.")
        self.apply_range_btn = QtWidgets.QPushButton("Apply time window")
        self.apply_range_btn.setToolTip("Apply the start/end times above.")
        self.reset_view_btn = QtWidgets.QPushButton("Show full range")
        self.reset_view_btn.setToolTip("Zoom to the full time range.")

        range_controls.addWidget(QtWidgets.QLabel("Start time (UTC)"))
        range_controls.addWidget(self.start_edit)
        range_controls.addWidget(QtWidgets.QLabel("End time (UTC)"))
        range_controls.addWidget(self.end_edit)
        range_controls.addWidget(self.apply_range_btn)
        range_controls.addWidget(self.reset_view_btn)
        range_controls.addStretch(1)

        axis = pg.DateAxisItem(orientation="bottom")
        self.view_box = RangeViewBox(self._show_context_menu)
        self.plot_widget = pg.PlotWidget(axisItems={"bottom": axis}, viewBox=self.view_box)
        self.plot_widget.setToolTip("Right-click for options. Drag to pan or zoom.")
        range_tip = QtWidgets.QLabel("Tip: right-click the plot to set the start or end time.")
        range_tip.setWordWrap(True)
        range_tip.setToolTip("Use the context menu to set the start or end of the time window.")
        self.empty_label = QtWidgets.QLabel("Select one or more metrics on the left to see a plot here.")
        self.empty_label.setWordWrap(True)
        layout.addLayout(controls)
        layout.addLayout(range_controls)
        layout.addWidget(range_tip)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.plot_widget)

        self.plot_manager = PlotManager(self.plot_widget)
        self.range_region = None
        self._last_series_map: Dict[str, pd.Series] = {}
        self._full_range: tuple[float, float] | None = None
        self._decay_markers: list[pg.InfiniteLine] = []

        self.range_checkbox.toggled.connect(self._toggle_range)
        self.clear_range_btn.clicked.connect(self._clear_range)
        self.mode_combo.currentTextChanged.connect(self._set_mouse_mode)
        self.apply_range_btn.clicked.connect(self._apply_range)
        self.reset_view_btn.clicked.connect(self._reset_view)

        self._set_mouse_mode(self.mode_combo.currentText())

    def plot_series(self, series_map: Dict[str, pd.Series]):
        self._last_series_map = series_map
        self.empty_label.setVisible(not bool(series_map))
        style = {}
        axis_colors: Dict[str, str] = {}
        axis_labels: Dict[str, str] = {}
        color_idx = 0
        for name in series_map.keys():
            base = self._base_metric(name)
            if base not in axis_colors:
                axis_colors[base] = OKABE_ITO[color_idx % len(OKABE_ITO)]
                axis_labels[base] = metric_axis_label(base)
                color_idx += 1

        for name in series_map.keys():
            color = axis_colors[self._base_metric(name)]
            if name.endswith("(raw)"):
                qcolor = pg.mkColor(color)
                qcolor.setAlpha(80)
                style[name] = {
                    "pen": None,
                    "symbol": "o",
                    "symbolSize": 4,
                    "symbolBrush": pg.mkBrush(qcolor),
                    "symbolPen": pg.mkPen(qcolor),
                }
            else:
                style[name] = {
                    "pen": pg.mkPen(color=color, width=1.5),
                    "symbol": None,
                }
        self.plot_manager.set_series(series_map, style=style, axis_colors=axis_colors, axis_labels=axis_labels)
        self._update_range_from_series(series_map)

    def export_plot(self, path: Path):
        exporter = pg.exporters.ImageExporter(self.plot_widget.plotItem)
        exporter.export(str(path))

    def _set_mouse_mode(self, mode: str):
        view = self.plot_widget.getViewBox()
        if mode.lower().startswith("pan"):
            view.setMouseMode(pg.ViewBox.PanMode)
        else:
            view.setMouseMode(pg.ViewBox.RectMode)

    def _toggle_range(self, enabled: bool):
        if enabled and self.range_region is None:
            self.range_region = pg.LinearRegionItem()
            self.range_region.setZValue(10)
            self.range_region.setMovable(False)
            self.range_region.sigRegionChanged.connect(self._on_region_changed)
            self.plot_widget.addItem(self.range_region)
            self.clear_range_btn.setEnabled(True)
        elif not enabled and self.range_region is not None:
            self.plot_widget.removeItem(self.range_region)
            self.range_region = None
            self.clear_range_btn.setEnabled(False)
            self.time_range_changed.emit(None, None)
        self.range_enabled_changed.emit(enabled)

    def _update_range_from_series(self, series_map: Dict[str, pd.Series]):
        if not series_map:
            self._full_range = None
            return
        min_x, max_x = None, None
        for series in series_map.values():
            if series.empty:
                continue
            if isinstance(series.index, pd.DatetimeIndex):
                xs = series.index.view("int64") / 1e9
            else:
                xs = series.index.to_numpy(dtype=float)
            if xs.size == 0:
                continue
            min_x = xs.min() if min_x is None else min(min_x, xs.min())
            max_x = xs.max() if max_x is None else max(max_x, xs.max())
        if min_x is None or max_x is None:
            return

        self._full_range = (float(min_x), float(max_x))
        self._set_datetime_edits(min_x, max_x)

        if self.range_checkbox.isChecked() and self.range_region is not None:
            self.range_region.setRegion((min_x, max_x))
            self._on_region_changed()

    def _on_region_changed(self):
        if self.range_region is None:
            return
        start, end = self.range_region.getRegion()
        self._set_datetime_edits(start, end)
        start_dt = pd.to_datetime(start, unit="s", utc=True)
        end_dt = pd.to_datetime(end, unit="s", utc=True)
        self.time_range_changed.emit(start_dt, end_dt)

    def _clear_range(self):
        self._reset_view()

    def set_decay_events(self, events):
        for marker in self._decay_markers:
            self.plot_widget.removeItem(marker)
        self._decay_markers.clear()

        if not events:
            return
        for event in events:
            start_x = event.start.timestamp()
            end_x = event.end.timestamp()
            start_line = pg.InfiniteLine(
                pos=start_x,
                angle=90,
                movable=False,
                pen=pg.mkPen("#FF6B6B", width=1),
                label=event.label,
                labelOpts={"position": 0.9, "color": "#FF6B6B"},
            )
            end_line = pg.InfiniteLine(
                pos=end_x,
                angle=90,
                movable=False,
                pen=pg.mkPen("#FF6B6B", width=1),
            )
            self.plot_widget.addItem(start_line)
            self.plot_widget.addItem(end_line)
            self._decay_markers.extend([start_line, end_line])

    def _reset_view(self):
        if self._full_range is None:
            return
        start, end = self._full_range
        if self.range_checkbox.isChecked():
            if self.range_region is None:
                self._toggle_range(True)
            if self.range_region is not None:
                self.range_region.setRegion((start, end))
        self.plot_widget.setXRange(start, end, padding=0)
        self.time_range_changed.emit(pd.to_datetime(start, unit="s", utc=True), pd.to_datetime(end, unit="s", utc=True))

    def _apply_range(self):
        start_sec = self.start_edit.dateTime().toSecsSinceEpoch()
        end_sec = self.end_edit.dateTime().toSecsSinceEpoch()
        if start_sec > end_sec:
            start_sec, end_sec = end_sec, start_sec
        if not self.range_checkbox.isChecked():
            self.range_checkbox.setChecked(True)
        if self.range_region is not None:
            self.range_region.setRegion((start_sec, end_sec))
        self.plot_widget.setXRange(start_sec, end_sec, padding=0)
        self.time_range_changed.emit(pd.to_datetime(start_sec, unit="s", utc=True), pd.to_datetime(end_sec, unit="s", utc=True))

    def _set_datetime_edits(self, start_sec: float, end_sec: float):
        start_dt = QtCore.QDateTime.fromSecsSinceEpoch(int(start_sec), QtCore.Qt.UTC)
        end_dt = QtCore.QDateTime.fromSecsSinceEpoch(int(end_sec), QtCore.Qt.UTC)
        self.start_edit.blockSignals(True)
        self.end_edit.blockSignals(True)
        self.start_edit.setDateTime(start_dt)
        self.end_edit.setDateTime(end_dt)
        self.start_edit.blockSignals(False)
        self.end_edit.blockSignals(False)

    def _set_start_from_x(self, x_sec: float):
        self._set_datetime_edits(x_sec, self.end_edit.dateTime().toSecsSinceEpoch())
        self._apply_range()

    def _set_end_from_x(self, x_sec: float):
        self._set_datetime_edits(self.start_edit.dateTime().toSecsSinceEpoch(), x_sec)
        self._apply_range()

    def _base_metric(self, name: str) -> str:
        for suffix in (" (raw)", " (filtered)"):
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return name

    def _show_context_menu(self, x_sec: float):
        menu = QtWidgets.QMenu(self)
        set_start_action = menu.addAction("Set start time here")
        set_end_action = menu.addAction("Set end time here")
        menu.addSeparator()
        if self.range_checkbox.isChecked():
            zoom_window_action = menu.addAction("Zoom to time window")
            clear_window_action = menu.addAction("Clear time window")
        else:
            enable_window_action = menu.addAction("Enable time window")
        center_here_action = menu.addAction("Center view here")
        full_range_action = menu.addAction("Show full range")
        copy_time_action = menu.addAction("Copy timestamp (UTC)")
        action = menu.exec(QtGui.QCursor.pos())

        if action == set_start_action:
            self._set_start_from_x(x_sec)
        elif action == set_end_action:
            self._set_end_from_x(x_sec)
        elif self.range_checkbox.isChecked() and action == zoom_window_action:
            self._apply_range()
        elif self.range_checkbox.isChecked() and action == clear_window_action:
            self._clear_range()
        elif not self.range_checkbox.isChecked() and action == enable_window_action:
            self.range_checkbox.setChecked(True)
        elif action == center_here_action:
            self._center_view_on_x(x_sec)
        elif action == full_range_action:
            self._reset_view()
        elif action == copy_time_action:
            dt = pd.to_datetime(x_sec, unit="s", utc=True)
            QtWidgets.QApplication.clipboard().setText(dt.isoformat())

    def _center_view_on_x(self, x_sec: float):
        view = self.plot_widget.getViewBox()
        x_range, _ = view.viewRange()
        width = x_range[1] - x_range[0]
        if width <= 0:
            return
        view.setXRange(x_sec - width / 2, x_sec + width / 2, padding=0)
