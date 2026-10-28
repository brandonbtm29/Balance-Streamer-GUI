"""The "Troubleshooting" box on the Settings tab: Open Log Folder and Copy Diagnostics."""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

import crash_log
import diagnostics

from . import __version__
from .paths import APP_DIR, CONFIG_DIR, DATA_DIR

log = logging.getLogger(__name__)

APP_NAME = "Balance Streamer"
_NO_PORT = ("", "No Ports Found")


def balance_summary(tabs):
    """Extra Copy Diagnostics lines: how many balances there are, and each one's brand and port.

    Tab names are left out (they are the user's own text); brands and port names are not secret.
    """
    lines = {"Balances configured": str(len(tabs))}
    for number, tab in enumerate(tabs, 1):
        brand = tab.combo_brand.currentText() or "no brand chosen"
        port = tab.combo_com.currentText()
        port = "no port chosen" if port in _NO_PORT else port
        thread = tab.serial_thread
        state = "connected" if thread is not None and thread.isRunning() else "not connected"
        if getattr(tab, "recording", False):
            state += ", recording"
        lines[f"Balance {number}"] = f"{brand} on {port} ({state})"
    return lines


class DiagnosticsPanel(QGroupBox):
    def __init__(self, app_ref, parent=None):
        super().__init__("Troubleshooting", parent)
        self.app_ref = app_ref
        lay = QVBoxLayout(self)
        info = QLabel(
            "If something goes wrong, the log file says what happened. Copy Diagnostics copies the "
            "app version, your system, where the app keeps its files and the end of the log, ready "
            "to paste into a GitHub issue or an email."
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        row = QHBoxLayout()
        self.btn_open_logs = QPushButton("Open Log Folder")
        self.btn_open_logs.clicked.connect(self.open_log_folder)
        self.btn_copy = QPushButton("Copy Diagnostics")
        self.btn_copy.clicked.connect(self.copy_diagnostics)
        row.addWidget(self.btn_open_logs)
        row.addWidget(self.btn_copy)
        lay.addLayout(row)
        self.lbl_status = QLabel("")
        self.lbl_status.setWordWrap(True)
        lay.addWidget(self.lbl_status)

    def report(self):
        """The diagnostics text (already redacted: home folder shortened, secrets blanked)."""
        return diagnostics.report(
            APP_NAME,
            __version__,
            APP_DIR,
            settings_dir=CONFIG_DIR,
            data_dir=DATA_DIR,
            log_path=crash_log.log_path(),
            extra=balance_summary(self.app_ref.tab_objects),
        )

    def copy_diagnostics(self):
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)  # asks git for local changes
        try:
            text = self.report()
        finally:
            QApplication.restoreOverrideCursor()
        QApplication.clipboard().setText(text)
        self.lbl_status.setText("Diagnostics copied. Paste them into a GitHub issue or an email.")

    def open_log_folder(self):
        try:
            diagnostics.open_folder(diagnostics.log_folder(crash_log.log_path()))
        except OSError as e:
            log.warning("Couldn't open the log folder: %s", e)
            QMessageBox.warning(self, "Open Log Folder", f"Couldn't open the log folder.\n\n{e}")
