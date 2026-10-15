"""The "Desktop Shortcut" box on the Settings tab."""

import logging
import os
import sys

from PyQt6.QtWidgets import QGroupBox, QLabel, QMessageBox, QPushButton, QVBoxLayout

from . import shortcut
from .update_panel import _Task

log = logging.getLogger(__name__)

_WHERE = {
    "win32": "a shortcut on your desktop that opens the app without the black console window",
    "darwin": "a Balance Streamer app on your desktop (drag it to the Dock or Applications if you like)",
}


class ShortcutPanel(QGroupBox):
    def __init__(self, parent=None):
        super().__init__("Desktop Shortcut", parent)
        lay = QVBoxLayout(self)
        what = _WHERE.get(sys.platform, "a launcher on your desktop")
        info = QLabel(
            f"Creates {what}. It starts this copy of the app, so it keeps working after updates. "
            "Pressing the button again replaces the old shortcut. After an update the app refreshes "
            "the shortcut by itself."
        )
        info.setWordWrap(True)
        lay.addWidget(info)
        self.btn_create = QPushButton("Create Desktop Shortcut")
        self.btn_create.clicked.connect(self.create)
        lay.addWidget(self.btn_create)

    def create(self):
        try:
            path = shortcut.create_shortcut()
        except shortcut.ShortcutError as e:
            log.warning("Desktop shortcut: %s", e)
            QMessageBox.warning(self, "Desktop Shortcut", str(e))
            return
        except (OSError, ValueError) as e:
            log.exception("Couldn't create the desktop shortcut")
            QMessageBox.warning(self, "Desktop Shortcut", f"Couldn't create the shortcut:\n{e}")
            return
        log.info("Created desktop shortcut %s", path)
        QMessageBox.information(self, "Desktop Shortcut", f"Created:\n{path}")

    # --- at startup ---------------------------------------------------------------------------

    def startup_check(self):
        """Refresh an outdated shortcut, or offer one the first time on this computer."""
        self._task = _Task(self._startup_work, self)
        self._task.done.connect(self._startup_done)
        self._task.start()

    @staticmethod
    def _startup_work(_say):
        # Runs in a background thread: finding the desktop on Windows starts PowerShell.
        desktop = shortcut.desktop_folder()
        exists = os.path.exists(shortcut.shortcut_path(desktop))
        action = shortcut.startup_action(exists, shortcut.load_state())
        if action == "refresh":
            return "refreshed", shortcut.create_shortcut(desktop)
        return action, None

    def _startup_done(self, result):
        if isinstance(result, Exception):
            log.warning("Desktop shortcut check failed: %s", result)
            return
        action, value = result
        if action == "refreshed":
            log.info("Refreshed desktop shortcut %s", value)
            self._status("Desktop shortcut updated for this version.")
        elif action == "offer":
            shortcut.save_state(shortcut_offered=True)  # ask only once on this computer
            answer = QMessageBox.question(
                self,
                "Desktop Shortcut",
                "Put a Balance Streamer icon on your desktop?\n\n"
                "You can also do this later in Settings → Application Settings.",
            )
            if answer == QMessageBox.StandardButton.Yes:
                self.create()

    def _status(self, text):
        window = self.window()
        if hasattr(window, "statusBar"):
            window.statusBar().showMessage(text, 8000)
