"""Version in the corner, the out-of-date warning, the desktop shortcut at startup, launchers."""

import os
import plistlib
import sys

import pytest
from PyQt6.QtCore import QEventLoop, QTimer

import balance_streamer
from balance_streamer import shortcut, updater
from balance_streamer.paths import REPO_DIR

NEWER = updater.Release("99.0.0", "v99.0.0", "Balance Streamer 99.0.0", "Notes", "https://example.invalid")
SAME = updater.Release(balance_streamer.__version__, "v" + balance_streamer.__version__, "Same", "", "")


def test_version_shows_in_the_corner(window):
    text = window.version_status.text()
    assert balance_streamer.__version__ in text
    assert window.statusBar().isAncestorOf(window.version_status)


@pytest.mark.parametrize(
    ("result", "expected"),
    [(None, "Balance Streamer"), (NEWER, "out of date"), (SAME, "up to date"), (LookupError("offline"), "")],
)
def test_version_status_states(window, result, expected):
    window.version_status.show_result(result)
    assert expected in window.version_status.text()
    if isinstance(result, Exception):
        assert "offline" in window.version_status.toolTip()


def _wait_for(signal, timeout_ms=5000):
    loop = QEventLoop()
    signal.connect(lambda *_: loop.quit())
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()


def test_quiet_startup_check_warns_without_a_dialog(window, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr(updater, "latest_release", lambda: NEWER)
    monkeypatch.setattr(QMessageBox, "exec", lambda self: pytest.fail("a dialog opened during a quiet check"))
    panel = window.settings_tab.update_panel
    panel.check(quiet=True)
    _wait_for(panel.checked)
    panel._task.wait(5)
    assert "out of date" in window.version_status.text()
    assert panel.latest == NEWER

    offered = []
    monkeypatch.setattr(panel, "_offer", offered.append)
    window.show_update()  # what clicking "Update to …" in the corner does
    assert window.tabs.currentWidget() is window.settings_tab
    assert offered == [NEWER]


def test_check_on_start_setting(window):
    panel = window.settings_tab.update_panel
    assert panel.check_on_start()
    panel.chk_on_start.setChecked(False)
    assert window.config["check_updates_on_start"] is False


@pytest.mark.parametrize(
    ("exists", "state", "expected"),
    [
        (False, {}, "offer"),  # first start on this computer
        (False, {"shortcut_offered": True}, "nothing"),  # asked before, or the user deleted it
        (True, {"shortcut_version": "0.0.1"}, "refresh"),  # made by an older version
        (True, {"shortcut_version": balance_streamer.__version__}, "nothing"),
    ],
)
def test_shortcut_startup_action(exists, state, expected):
    assert shortcut.startup_action(exists, state) == expected


def test_shortcut_state_round_trip():
    assert shortcut.load_state() == {}
    shortcut.save_state(shortcut_offered=True)
    shortcut.save_state(shortcut_version="1.2.3")
    assert shortcut.load_state() == {"shortcut_offered": True, "shortcut_version": "1.2.3"}


def test_mac_shortcut_has_icon_on_every_platform(tmp_path):
    app = shortcut._create_mac(str(tmp_path))
    with open(os.path.join(app, "Contents", "Info.plist"), "rb") as f:
        assert plistlib.load(f)["CFBundleIconFile"] == "AppIcon"
    assert os.path.getsize(os.path.join(app, "Contents", "Resources", "AppIcon.icns")) > 10_000


def test_repo_mac_launcher_app():
    app = os.path.join(REPO_DIR, "Balance Streamer.app", "Contents")
    with open(os.path.join(app, "Info.plist"), "rb") as f:
        info = plistlib.load(f)
    assert info["CFBundleExecutable"] == "launch" and info["CFBundleIconFile"] == "AppIcon"
    assert os.path.exists(os.path.join(app, "Resources", "AppIcon.icns"))
    launch = os.path.join(app, "MacOS", "launch")
    text = open(launch, encoding="utf-8").read()
    assert ".venv/bin/python" in text and "multi_balance_stream.py" in text
    if os.name != "nt":
        assert os.access(launch, os.X_OK)


def test_windows_launcher_uses_pythonw():
    text = open(os.path.join(REPO_DIR, "Launch_Windows.bat"), encoding="utf-8").read()
    assert "pythonw" in text and 'start ""' in text


def test_startup_error_is_reported(tmp_path, monkeypatch):
    sys.path.insert(0, REPO_DIR)
    import multi_balance_stream as entry

    shown = []
    monkeypatch.setattr(entry, "HERE", str(tmp_path))
    monkeypatch.setattr(entry, "_show_message", lambda title, text: shown.append((title, text)))
    try:
        raise ModuleNotFoundError("No module named 'PyQt6'")
    except ModuleNotFoundError:
        entry.report_startup_error()
    assert "No module named 'PyQt6'" in (tmp_path / "startup-error.log").read_text(encoding="utf-8")
    assert shown and "couldn't start" in shown[0][0]
