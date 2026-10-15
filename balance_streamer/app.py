"""Start the app."""

import logging
import sys

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication

from . import __version__
from .logs import install_excepthook, setup_logging
from .main_window import MultiBalanceApp
from .paths import ICON_FILE, enter_data_dir
from .theme import apply_theme


def main():
    enter_data_dir()
    setup_logging()
    install_excepthook()
    logging.getLogger(__name__).info("Balance Streamer %s starting", __version__)
    if sys.platform == "win32":
        # Its own taskbar group and icon, instead of being grouped with other Python programs.
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("brandonbtm29.BalanceStreamer")
    app = QApplication(sys.argv)
    app.setApplicationName("Balance Streamer")
    app.setWindowIcon(QIcon(ICON_FILE))  # window, taskbar and Dock icon

    window = MultiBalanceApp()
    apply_theme(dark=window.config.get("dark_mode", True), app=app)

    window.showMaximized()
    window.start_background_tasks()

    sys.exit(app.exec())
