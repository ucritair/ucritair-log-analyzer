import sys
from PySide6 import QtCore, QtWidgets

from app.core.logging import setup_logging
from app.core.state import AppState
from app.core.config import ProcessingConfig, FilterConfig
from app.ui.main_window import MainWindow


def run_app() -> None:
    setup_logging()

    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
    QtCore.QCoreApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

    app = QtWidgets.QApplication(sys.argv)

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
