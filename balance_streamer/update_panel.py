"""The "Updates" box on the Settings tab: check GitHub, update and restart."""

import logging

from PyQt6.QtCore import Qt, QThread, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QVBoxLayout,
)

from . import __version__, updater

log = logging.getLogger(__name__)


class _Task(QThread):
    """Run one slow function (network, git, pip) off the GUI thread."""

    done = pyqtSignal(object)
    progress = pyqtSignal(str)

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn

    def run(self):
        try:
            self.done.emit(self._fn(self.progress.emit))
        except LookupError as e:  # an expected problem with a plain message (offline, no releases)
            log.info("Update check: %s", e)
            self.done.emit(e)
        except Exception as e:  # handed back to the GUI thread and shown there
            log.exception("Update task failed")
            self.done.emit(e)


class UpdatePanel(QGroupBox):
    def __init__(self, app_ref, parent=None):
        super().__init__("Updates", parent)
        self.app_ref = app_ref
        self._task = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"You are running Balance Streamer <b>{__version__}</b>."))
        self.lbl_status = QLabel("Checks GitHub for a newer release only when you press the button.")
        self.lbl_status.setWordWrap(True)
        self.lbl_status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.lbl_status)
        row = QHBoxLayout()
        self.btn_check = QPushButton("Check for Updates")
        self.btn_check.clicked.connect(self.check)
        btn_page = QPushButton("Open Release Page")
        btn_page.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(updater.RELEASES_PAGE)))
        row.addWidget(self.btn_check)
        row.addWidget(btn_page)
        lay.addLayout(row)

    # --- checking ------------------------------------------------------------------------

    def check(self):
        self.btn_check.setEnabled(False)
        self.lbl_status.setText("Checking GitHub…")
        self._start(lambda _say: updater.latest_release(), self._checked)

    def _checked(self, result):
        self.btn_check.setEnabled(True)
        if isinstance(result, Exception):
            msg = str(result) if isinstance(result, LookupError) else f"The check failed: {result}"
            self.lbl_status.setText(msg)
            return
        release = result
        if not updater.is_newer(release.version):
            self.lbl_status.setText(f"You have the latest version ({__version__}).")
            return
        self.lbl_status.setText(f"Version {release.version} is available.")
        self._offer(release)

    def _offer(self, release):
        ready = updater.update_readiness()
        notes = release.notes.strip()
        if len(notes) > 1500:
            notes = notes[:1500].rsplit("\n", 1)[0] + "\n…"
        box = QMessageBox(self)
        box.setWindowTitle("Update available")
        box.setText(f"<b>{release.name}</b> is available. You have {__version__}.")
        box.setDetailedText(notes or "No release notes.")
        btn_page = box.addButton("Open Release Page", QMessageBox.ButtonRole.HelpRole)
        btn_update = None
        if ready.ok:
            box.setInformativeText(
                "Update now? The app saves your tabs, downloads the new version, reinstalls its "
                "requirements and restarts. Connected balances are disconnected." + self._recording_warning()
            )
            btn_update = box.addButton("Update and Restart", QMessageBox.ButtonRole.AcceptRole)
        else:
            box.setInformativeText(ready.reason)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        clicked = box.clickedButton()
        if clicked is btn_page:
            QDesktopServices.openUrl(QUrl(release.url))
        elif btn_update is not None and clicked is btn_update:
            self._update(release)

    def _recording_warning(self):
        recording = [t.tab_name for t in self.app_ref.tab_objects if getattr(t, "recording", False)]
        if not recording:
            return ""
        return (
            "\n\nRecording is running in: " + ", ".join(recording) + ". It will stop; the data so far is "
            "kept in the backup file and can be brought back with Recover Session."
        )

    # --- updating ------------------------------------------------------------------------

    def _update(self, release):
        self.app_ref.save_config()
        for tab in self.app_ref.tab_objects:
            if hasattr(tab, "save_tab_settings"):
                tab.save_tab_settings()
        self.btn_check.setEnabled(False)
        self._progress = QProgressDialog("Starting…", None, 0, 0, self)
        self._progress.setWindowTitle(f"Updating to {release.version}")
        self._progress.setWindowModality(Qt.WindowModality.ApplicationModal)
        self._progress.setMinimumDuration(0)
        self._progress.show()
        self._start(lambda say: updater.update_to(release.tag, progress=say), self._updated)

    def _updated(self, result):
        self._progress.close()
        self.btn_check.setEnabled(True)
        if isinstance(result, Exception):
            result = updater.UpdateResult(False, f"The update failed: {result}")
        if not result.ok:
            self.lbl_status.setText("The update didn't finish. See the message for details.")
            QMessageBox.warning(self, "Update", result.message)
            return
        self.lbl_status.setText(result.message + " Restarting…")
        QMessageBox.information(self, "Update", result.message + "\n\nThe app will now restart.")
        self.app_ref.restart_app()

    def _start(self, fn, on_done):
        self._task = _Task(fn, self)
        self._task.done.connect(on_done)
        if getattr(self, "_progress", None) is not None:
            self._task.progress.connect(self._progress.setLabelText)
        self._task.start()
