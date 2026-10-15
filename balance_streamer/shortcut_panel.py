"""The "Desktop Shortcut" box on the Settings tab."""

import logging
import sys

from PyQt6.QtWidgets import QGroupBox, QLabel, QMessageBox, QPushButton, QVBoxLayout

from . import shortcut

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
            "Pressing the button again replaces the old shortcut."
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
