from __future__ import annotations

from PySide6 import QtCore
import pandas as pd


class PandasTableModel(QtCore.QAbstractTableModel):
    def __init__(self, df: pd.DataFrame | None = None):
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()

    def set_dataframe(self, df: pd.DataFrame):
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent=QtCore.QModelIndex()) -> int:  # noqa: N802
        return len(self._df.index)

    def columnCount(self, parent=QtCore.QModelIndex()) -> int:  # noqa: N802
        return len(self._df.columns)

    def data(self, index: QtCore.QModelIndex, role=QtCore.Qt.DisplayRole):
        if not index.isValid() or role != QtCore.Qt.DisplayRole:
            return None
        value = self._df.iloc[index.row(), index.column()]
        return str(value)

    def headerData(self, section: int, orientation, role=QtCore.Qt.DisplayRole):  # noqa: N802
        if role != QtCore.Qt.DisplayRole:
            return None
        if orientation == QtCore.Qt.Horizontal:
            return str(self._df.columns[section])
        return str(self._df.index[section])
