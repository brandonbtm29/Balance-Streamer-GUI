"""Start the app."""

import logging
import sys

import qdarktheme
from PyQt6.QtWidgets import QApplication

from . import __version__
from .logs import install_excepthook, setup_logging
from .main_window import MultiBalanceApp
from .paths import enter_data_dir


def main():
    enter_data_dir()
    setup_logging()
    install_excepthook()
    logging.getLogger(__name__).info("Balance Streamer %s starting", __version__)
    app = QApplication(sys.argv)

    window = MultiBalanceApp()
    theme = "dark" if window.config.get("dark_mode", True) else "light"
    app.setStyleSheet(qdarktheme.load_stylesheet(theme))

    window.showMaximized()

    sys.exit(app.exec())
