"""Start the app."""

import logging
import sys

from PyQt6.QtWidgets import QApplication

from . import __version__
from .logs import install_excepthook, setup_logging
from .main_window import MultiBalanceApp
from .paths import enter_data_dir
from .theme import apply_theme


def main():
    enter_data_dir()
    setup_logging()
    install_excepthook()
    logging.getLogger(__name__).info("Balance Streamer %s starting", __version__)
    app = QApplication(sys.argv)

    window = MultiBalanceApp()
    apply_theme(dark=window.config.get("dark_mode", True), app=app)

    window.showMaximized()

    sys.exit(app.exec())
