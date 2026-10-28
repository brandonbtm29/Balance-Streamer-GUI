"""Version in the corner, the out-of-date warning, the desktop shortcut at startup, launchers,
start-up errors and restarting."""

import logging
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
    # Not set up yet: Launch_Mac.command sets it up; Troubleshoot_Mac.command shows the messages.
    assert "Double-click Launch_Mac.command" in text and "Troubleshoot_Mac.command" in text
    assert "README" not in text
    with open(launch, "rb") as f:
        assert b"\r" not in f.read()  # bash needs LF line endings
    if os.name != "nt":
        assert os.access(launch, os.X_OK)


def test_windows_launcher_uses_pythonw():
    text = open(os.path.join(REPO_DIR, "Launch_Windows.bat"), encoding="utf-8").read()
    assert "pythonw" in text and 'start ""' in text


def _read_log(path):
    for h in logging.getLogger().handlers:
        h.flush()
    with open(path, encoding="utf-8") as f:
        return f.read()


def test_startup_error_is_logged_and_shown(tmp_path, monkeypatch):
    import crash_log

    sys.path.insert(0, REPO_DIR)
    import multi_balance_stream as entry

    shown = []
    monkeypatch.setattr(entry, "_show_message", lambda title, text: shown.append((title, text)))
    crash_log._reset_for_tests()
    try:
        path = crash_log.setup("balance_streamer", str(tmp_path / "logs"), qt_dialog=False)
        try:
            raise ModuleNotFoundError("No module named 'PyQt6'")
        except ModuleNotFoundError:
            entry.report_startup_error()
        text = _read_log(path)
        assert "Balance Streamer couldn't start" in text and "No module named 'PyQt6'" in text
        assert shown and "couldn't start" in shown[0][0]
        assert "No module named 'PyQt6'" in shown[0][1] and path in shown[0][1]

        crash_log._reset_for_tests()  # logging couldn't be set up at all: still say why
        shown.clear()
        try:
            raise ModuleNotFoundError("No module named 'serial'")
        except ModuleNotFoundError:
            entry.report_startup_error()
        assert "No module named 'serial'" in shown[0][1] and "couldn't be saved" in shown[0][1]
    finally:
        crash_log._reset_for_tests()


def _launcher(name):
    with open(os.path.join(REPO_DIR, name), encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize(
    ("name", "setup"),
    [("Launch_Windows.bat", "Setup_Windows.bat"), ("Launch_Mac.command", "Setup_Mac.command")],
)
def test_launchers_set_up_on_first_run_and_check_before_starting(name, setup):
    text = _launcher(name)
    assert "requirements.txt" in text and "a minute or two" in text  # first run installs the app
    assert "import PyQt6.QtWidgets" in text and setup in text  # visible check, points at the repair
    assert "multi_balance_stream.py" in text


def test_mac_launcher_starts_detached_and_closes_terminal():
    text = _launcher("Launch_Mac.command")
    assert "start_new_session=True" in text and "osascript" in text and "tty" in text


@pytest.mark.parametrize("name", ["Troubleshoot_Windows.bat", "Troubleshoot_Mac.command"])
def test_troubleshooting_launchers_show_output(name):
    text = _launcher(name)
    assert "multi_balance_stream.py" in text
    assert "pythonw" not in text and "start_new_session" not in text  # runs in the visible window
    assert "pause" in text.lower() or "read -r" in text


@pytest.mark.skipif(os.name == "nt", reason="Windows has no executable bit")
@pytest.mark.parametrize("name", ["Launch_Mac.command", "Troubleshoot_Mac.command", "Setup_Mac.command"])
def test_mac_launchers_are_executable(name):
    assert os.access(os.path.join(REPO_DIR, name), os.X_OK)


def _record_restart(monkeypatch):
    """Stand-ins for releasing the lock, starting the new copy and quitting, in call order."""
    import subprocess

    from PyQt6.QtCore import QProcess
    from PyQt6.QtWidgets import QApplication

    import single_instance

    calls = []
    monkeypatch.setattr(single_instance, "release", lambda: calls.append("release"))
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: calls.append("start"))
    monkeypatch.setattr(QProcess, "startDetached", lambda *a, **k: calls.append("start"))
    monkeypatch.setattr(QApplication, "quit", lambda *a: calls.append("quit"))
    return calls


def test_restart_releases_the_single_instance_lock_first(window, monkeypatch):
    calls = _record_restart(monkeypatch)
    window.restart_app()  # Restart, Update and Restart, and a new settings folder all use this
    assert calls == ["release", "start", "quit"]


def test_panel_order_restart_lets_go_of_the_balances_first(window, monkeypatch):
    """Apply and Restart (Panel Management) restarts like Restart: ports closed, lock released."""
    calls = _record_restart(monkeypatch)
    tab = window.tab_objects[0]
    monkeypatch.setattr(tab, "serial_thread", object())  # as if this balance were connected
    monkeypatch.setattr(tab, "disconnect_serial", lambda: calls.append("disconnect"))
    window.settings_tab.panel_widget.apply()
    assert calls == ["disconnect", "release", "start", "quit"]  # the new copy can open the ports


def _move_first_panel_to_the_end(panel_widget):
    lst = panel_widget.list_left
    lst.addItem(lst.takeItem(0))
    return [lst.item(i).text() for i in range(lst.count())]


def _saved_config(window):
    import json

    with open(window.config_path, encoding="utf-8") as f:
        return json.load(f)


def test_panel_order_is_saved_and_restarts_through_restart_app(window, monkeypatch):
    restarts = []
    monkeypatch.setattr(window, "restart_app", lambda: restarts.append(True))
    panel_widget = window.settings_tab.panel_widget
    new_order = _move_first_panel_to_the_end(panel_widget)
    panel_widget.apply()
    assert restarts == [True]
    assert _saved_config(window)["left_panel_order"] == new_order


def test_panel_order_asks_first_while_recording(window, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    restarts, questions = [], []
    monkeypatch.setattr(window, "restart_app", lambda: restarts.append(True))
    answer = [QMessageBox.StandardButton.No]
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: questions.append(a[2]) or answer[0])
    tab = window.tab_objects[0]
    monkeypatch.setattr(tab, "recording", True)
    panel_widget = window.settings_tab.panel_widget
    before = _saved_config(window).get("left_panel_order") if os.path.exists(window.config_path) else None
    new_order = _move_first_panel_to_the_end(panel_widget)

    panel_widget.apply()  # "No": nothing changes
    assert restarts == [] and len(questions) == 1
    assert tab.tab_name in questions[0] and "Recover Session" in questions[0]
    after = _saved_config(window).get("left_panel_order") if os.path.exists(window.config_path) else None
    assert after == before and window.config.get("left_panel_order") != new_order

    answer[0] = QMessageBox.StandardButton.Yes
    panel_widget.apply()
    assert restarts == [True]
    assert _saved_config(window)["left_panel_order"] == new_order


def test_failed_start_exits_cleanly(tmp_path):
    """An error after the window exists must exit with 1. It used to crash on the way out
    sometimes (exit code 139), when Python's shutdown destroyed the window and the QApplication.
    It needed the single-instance lock and didn't happen every time, so this takes a real
    (private) lock and tries a few times."""
    import subprocess
    import textwrap

    script = tmp_path / "fail_after_window.py"
    script.write_text(
        textwrap.dedent(
            f"""
            import os
            import sys

            sys.path.insert(0, {REPO_DIR!r})
            import single_instance
            from balance_streamer import app
            from balance_streamer.main_window import MultiBalanceApp

            # A real lock, but its own: never the one of a Balance Streamer that is open.
            _acquire = single_instance.acquire
            single_instance.acquire = lambda name: _acquire(f"{{name}} test {{os.getpid()}}")

            def fail(self):
                raise RuntimeError("start-up failed on purpose")

            MultiBalanceApp.start_background_tasks = fail  # after the window is shown
            app.main()
            """
        ),
        encoding="utf-8",
    )
    env = dict(
        os.environ,
        UAKRON_APP_DATA_DIR=str(tmp_path / "data"),
        UAKRON_SETTINGS_DIR=str(tmp_path / "settings"),
        QT_QPA_PLATFORM="offscreen",
    )
    env.pop("SINGLE_INSTANCE_OFF", None)  # the crash needed the guard
    for _ in range(3):
        result = subprocess.run(  # noqa: S603 - this Python running the script above
            [sys.executable, str(script)], env=env, capture_output=True, text=True, timeout=180
        )
        assert result.returncode == 1, result.stderr[-3000:]
        assert "start-up failed on purpose" in result.stderr


def test_failed_start_deletes_the_window_without_saving(qapp, monkeypatch):
    import matplotlib.pyplot as plt
    from PyQt6 import sip

    from balance_streamer import app
    from balance_streamer.main_window import MultiBalanceApp

    win = MultiBalanceApp()
    for tab in win.tab_objects:
        tab.update_timer.stop()
    saved = []
    monkeypatch.setattr(win, "save_config", lambda: saved.append("config"))
    monkeypatch.setattr(win, "remember_window_state", lambda: saved.append("window state"))
    win.show()
    app.discard_windows()
    assert sip.isdeleted(win)
    assert plt.get_fignums() == []
    assert saved == []  # deleted, not closed: a half-started app doesn't save over the settings
