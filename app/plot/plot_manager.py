from __future__ import annotations

from typing import Dict
import numpy as np
import pandas as pd
import pyqtgraph as pg


class PlotManager:
    AXIS_WIDTH = 110
    AXIS_SPACING = 12
    AXIS_ROW = 2

    def __init__(self, plot_widget: pg.PlotWidget):
        self.plot_widget = plot_widget
        self.plot_item = plot_widget.getPlotItem()
        self.plot_item.showGrid(x=True, y=True, alpha=0.3)
        self.plot_item.showAxis("right", False)
        self.plot_item.layout.setColumnSpacing(1, self.AXIS_SPACING)

        self.viewboxes: list[pg.ViewBox] = []
        self.axes: list[pg.AxisItem] = []
        self.axis_columns: list[int] = []
        self.curves: list[tuple[pg.ViewBox, pg.PlotDataItem]] = []
        self.right_axis = self.plot_item.getAxis("right")

        self.plot_item.vb.sigResized.connect(self._update_views)

    def _update_views(self):
        main_vb = self.plot_item.vb
        for vb in self.viewboxes:
            vb.setGeometry(main_vb.sceneBoundingRect())
            vb.linkedViewChanged(main_vb, vb.XAxis)

    def clear(self):
        for vb, curve in self.curves:
            vb.removeItem(curve)
        self.curves.clear()

        if self.right_axis is not None:
            self.right_axis.setVisible(False)
            self.right_axis.setLabel(text="")
            self.right_axis.linkToView(self.plot_item.vb)
            self.plot_item.layout.setColumnFixedWidth(2, 0)
            self.plot_item.layout.setColumnSpacing(2, 0)

        for axis in self.axes:
            self.plot_item.layout.removeItem(axis)
            axis.setVisible(False)
            if axis.scene() is not None:
                axis.scene().removeItem(axis)
            axis.setParentItem(None)
        self.axes.clear()

        for vb in self.viewboxes:
            self.plot_widget.scene().removeItem(vb)
        self.viewboxes.clear()

        for col in self.axis_columns:
            self.plot_item.layout.setColumnFixedWidth(col, 0)
            self.plot_item.layout.setColumnSpacing(col, 0)
        self.axis_columns.clear()

    def set_series(
        self,
        series_map: Dict[str, pd.Series],
        style: dict | None = None,
        axis_colors: dict | None = None,
        axis_labels: dict | None = None,
    ):
        self.clear()
        if not series_map:
            return

        groups: Dict[str, list[tuple[str, pd.Series]]] = {}
        for name, series in series_map.items():
            base = self._base_metric(name)
            groups.setdefault(base, []).append((name, series))

        for idx, (base, items) in enumerate(groups.items()):
            if idx == 0:
                vb = self.plot_item.vb
                axis = self.plot_item.getAxis("left")
            elif idx == 1 and self.right_axis is not None:
                axis = self.right_axis
                axis.setVisible(True)
                self.plot_item.layout.setColumnFixedWidth(2, self.AXIS_WIDTH)
                self.plot_item.layout.setColumnSpacing(2, self.AXIS_SPACING)
                axis.setWidth(self.AXIS_WIDTH)
                vb = pg.ViewBox()
                vb.setXLink(self.plot_item.vb)
                self.plot_widget.scene().addItem(vb)
                axis.linkToView(vb)
                self.viewboxes.append(vb)
            else:
                axis = pg.AxisItem("right")
                col = 3 + (idx - 2)
                self.plot_item.layout.addItem(axis, self.AXIS_ROW, col)
                self.plot_item.layout.setColumnFixedWidth(col, self.AXIS_WIDTH)
                self.plot_item.layout.setColumnSpacing(col, self.AXIS_SPACING)
                axis.setWidth(self.AXIS_WIDTH)
                vb = pg.ViewBox()
                vb.setXLink(self.plot_item.vb)
                self.plot_widget.scene().addItem(vb)
                axis.linkToView(vb)
                self.viewboxes.append(vb)
                self.axes.append(axis)
                self.axis_columns.append(col)

            label = axis_labels.get(base, base) if axis_labels else base
            axis.setLabel(text=label)
            axis.setStyle(tickTextOffset=8, tickLength=5, autoExpandTextSpace=True)
            if axis_colors and base in axis_colors:
                color = axis_colors[base]
                axis.setPen(pg.mkPen(color))
                axis.setTextPen(color)

            for name, series in items:
                x, y = self._series_to_xy(series)
                if style and name in style:
                    pen = style[name].get("pen")
                    symbol = style[name].get("symbol", None)
                    symbol_size = style[name].get("symbolSize", 4)
                    symbol_brush = style[name].get("symbolBrush", None)
                    symbol_pen = style[name].get("symbolPen", None)
                else:
                    pen = None
                    symbol = None
                    symbol_size = 4
                    symbol_brush = None
                    symbol_pen = None

                curve = pg.PlotDataItem(
                    x=x,
                    y=y,
                    pen=pen,
                    symbol=symbol,
                    symbolSize=symbol_size,
                    symbolBrush=symbol_brush,
                    symbolPen=symbol_pen,
                )
                vb.addItem(curve)
                self.curves.append((vb, curve))

        self._update_views()

    def _base_metric(self, name: str) -> str:
        for suffix in (" (raw)", " (filtered)"):
            if name.endswith(suffix):
                return name[: -len(suffix)]
        return name

    def _series_to_xy(self, series: pd.Series) -> tuple[np.ndarray, np.ndarray]:
        if series.empty:
            return np.array([]), np.array([])
        if isinstance(series.index, pd.DatetimeIndex):
            x = series.index.view(np.int64) / 1e9
        else:
            x = series.index.to_numpy(dtype=float)
        y = series.to_numpy(dtype=float)
        x, y = self._decimate(x, y)
        return x, y

    def _decimate(self, x: np.ndarray, y: np.ndarray, max_points: int = 8000) -> tuple[np.ndarray, np.ndarray]:
        if len(x) <= max_points:
            return x, y
        step = max(1, int(len(x) / max_points))
        return x[::step], y[::step]
