"""Start the app."""

import logging
import sys

from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

import single_instance

from .logs import setup_logging
from .main_window import MultiBalanceApp
from .paths import ICON_FILE, enter_data_dir
from .theme import apply_theme

log = logging.getLogger(__name__)


def main():
    setup_logging()  # first, so even a failed start leaves a trace in the log
    enter_data_dir()
    if sys.platform == "win32":
        # Its own taskbar group and icon, instead of being grouped with other Python programs.
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("brandonbtm29.BalanceStreamer")
    app = QApplication(sys.argv)
    app.setApplicationName("Balance Streamer")
    app.setWindowIcon(QIcon(ICON_FILE))  # window, taskbar and Dock icon

    # Only one copy at a time: two copies would fight over the same balances' ports.
    # Opening it again brings the running window to the front instead.
    guard = single_instance.acquire("Balance Streamer")
    if guard is None:
        sys.exit(0)

    try:
        window = MultiBalanceApp()
        guard.set_window(window)
        apply_theme(dark=window.config.get("dark_mode", True), app=app)

        window.showMaximized()
        window.start_background_tasks()
    except Exception:
        discard_windows()
        raise  # multi_balance_stream.py logs it and says why the app couldn't start

    sys.exit(app.exec())


def discard_windows():
    """After a failed start, delete the windows while the QApplication still exists.

    Otherwise the error keeps them alive until Python shuts down, which destroys the window and
    the QApplication in no fixed order: the app then sometimes crashed on the way out (exit code
    139 instead of 1). The windows are not closed, so nothing is saved over the settings.
    """
    try:
        import matplotlib.pyplot as plt

        plt.close("all")  # each balance tab's figure has a hidden pyplot window; let pyplot delete it
        for widget in QApplication.topLevelWidgets():
            widget.hide()
            widget.deleteLater()
        QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
        single_instance.release()  # opening the app again works while the error is still showing
    except Exception:  # never hide the error that stopped the start
        log.warning("Couldn't clean up after the failed start", exc_info=True)
