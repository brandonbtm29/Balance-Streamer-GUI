"""The "Updates" box on the Settings tab: check GitHub, update and restart."""

import logging
import threading

from PyQt6.QtCore import QObject, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QCheckBox,
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


class _Task(QObject):
    """Run one slow function (network, git, pip, PowerShell) off the GUI thread.

    A plain daemon thread rather than a QThread: if the window closes while a check is
    still waiting on the network, the app can quit without Qt aborting over a running
    thread. Results come back to the GUI thread through the queued `done` signal.
    """

    done = pyqtSignal(object)
    progress = pyqtSignal(str)
    _running = set()  # keeps tasks alive until they finish, even if their widget is gone

    def __init__(self, fn, parent=None):
        super().__init__(parent)
        self._fn = fn
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self):
        _Task._running.add(self)
        self._thread.start()

    def wait(self, timeout=None):
        self._thread.join(timeout)

    def _emit(self, signal, value):
        try:
            signal.emit(value)
        except RuntimeError:  # the widget that wanted the answer was closed meanwhile
            pass

    def _run(self):
        try:
            result = self._fn(lambda text: self._emit(self.progress, text))
        except LookupError as e:  # an expected problem with a plain message (offline, no releases)
            log.info("Update check: %s", e)
            result = e
        except Exception as e:  # handed back to the GUI thread and shown there
            log.exception("Background task failed")
            result = e
        self._emit(self.done, result)
        _Task._running.discard(self)


class UpdatePanel(QGroupBox):
    # Emitted after every check: the Release found, or the Exception that stopped the check.
    checked = pyqtSignal(object)

    def __init__(self, app_ref, parent=None):
        super().__init__("Updates", parent)
        self.app_ref = app_ref
        self._task = None
        self.latest = None  # newest Release seen, if it is newer than this version
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"You are running Balance Streamer <b>{__version__}</b>."))
        self.chk_on_start = QCheckBox("Check for updates when the app starts")
        self.chk_on_start.setChecked(self.check_on_start())
        self.chk_on_start.toggled.connect(self._set_check_on_start)
        lay.addWidget(self.chk_on_start)
        self.lbl_status = QLabel("Asks GitHub for the latest release. Nothing about you is sent.")
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

    def check_on_start(self):
        return bool(self.app_ref.config.get("check_updates_on_start", True))

    def _set_check_on_start(self, on):
        self.app_ref.config["check_updates_on_start"] = bool(on)
        self.app_ref.save_config()

    def check(self, quiet=False):
        """Ask GitHub for the latest release. Quiet checks (at startup) never open a dialog."""
        self.btn_check.setEnabled(False)
        self.lbl_status.setText("Checking GitHub…")
        self._start(lambda _say: updater.latest_release(), lambda result: self._checked(result, quiet))

    def offer_latest(self):
        """Show the update dialog for a release found earlier, or check again first."""
        if self.latest is not None:
            self._offer(self.latest)
        else:
            self.check()

    def _checked(self, result, quiet=False):
        self.btn_check.setEnabled(True)
        if isinstance(result, Exception):
            msg = str(result) if isinstance(result, LookupError) else f"The check failed: {result}"
            self.lbl_status.setText(msg)
            self.checked.emit(result)
            return
        release = result
        if not updater.is_newer(release.version):
            self.latest = None
            self.lbl_status.setText(f"You have the latest version ({__version__}).")
            self.checked.emit(release)
            return
        self.latest = release
        self.lbl_status.setText(f"Version {release.version} is available.")
        self.checked.emit(release)
        if not quiet:
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
        return self.app_ref.recording_warning()  # shared with Apply and Restart (panel order)

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


class VersionStatus(QLabel):
    """Bottom-right corner of the window: the version, and a warning when it is out of date."""

    update_clicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.linkActivated.connect(lambda _link: self.update_clicked.emit())
        self.setContentsMargins(8, 0, 8, 0)
        self.show_result(None)

    def show_result(self, result):
        """None = not checked yet; a Release; or the Exception from a failed check."""
        version = f"Balance Streamer {__version__}"
        if isinstance(result, updater.Release) and updater.is_newer(result.version):
            self.setText(
                f"<span style='color:#e67e22; font-weight:bold;'>⚠ {version} is out of date.</span> "
                f"<a href='update' style='color:#e67e22;'>Update to {result.version}…</a>"
            )
            self.setToolTip(f"{result.name} is available. Click to see what's new and update.")
        elif isinstance(result, updater.Release):
            self.setText(f"{version} <span style='color:#27ae60;'>✓ up to date</span>")
            self.setToolTip("This is the latest release on GitHub.")
        elif isinstance(result, Exception):
            self.setText(version)
            self.setToolTip(f"Couldn't check for updates: {result}")
        else:
            self.setText(version)
            self.setToolTip("")
