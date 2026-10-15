"""Start the app."""

import sys

import qdarktheme
from PyQt6.QtWidgets import QApplication

from .main_window import MultiBalanceApp
from .paths import enter_data_dir


def main():
    enter_data_dir()
    app = QApplication(sys.argv)

    window = MultiBalanceApp()
    theme = "dark" if window.config.get("dark_mode", True) else "light"
    app.setStyleSheet(qdarktheme.load_stylesheet(theme))

    window.showMaximized()

    sys.exit(app.exec())
