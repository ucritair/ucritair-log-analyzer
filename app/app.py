import os
import sys
from pathlib import Path
from PySide6 import QtCore, QtWidgets
import pyqtgraph as pg

from app.core.logging import setup_logging
from app.core.state import AppState
from app.core.config import ProcessingConfig, FilterConfig
from app.ui.main_window import MainWindow


def run_app() -> None:
    setup_logging()

    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    theme = os.environ.get("UCRITTER_THEME", "light").lower()
    theme_path = Path(__file__).resolve().parents[1] / "resources" / "themes" / f"{theme}.qss"
    if theme_path.exists():
        app.setStyleSheet(theme_path.read_text())
        if theme == "dark":
            pg.setConfigOption("background", "#0F1218")
            pg.setConfigOption("foreground", "#E6E9EF")
        else:
            pg.setConfigOption("background", "#FFFFFF")
            pg.setConfigOption("foreground", "#1C2129")

    state = AppState(
        datasets=[],
        active_standard_pack="us_epa_legacy",
        tz_display="local",
        processing_config=ProcessingConfig(),
        filter_config=FilterConfig(),
        threadpool=QtCore.QThreadPool.globalInstance(),
    )

    window = MainWindow(state)
    window.resize(1280, 820)
    window.show()

    sys.exit(app.exec())
