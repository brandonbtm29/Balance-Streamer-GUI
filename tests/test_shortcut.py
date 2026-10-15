"""Create Desktop Shortcut: each platform's launcher points at this copy of the app."""

import os
import plistlib
import subprocess
import sys

import pytest

from balance_streamer import shortcut
from balance_streamer.paths import REPO_DIR


def test_launch_command_starts_this_copy():
    program, args = shortcut.launch_command()
    assert os.path.exists(program)
    assert args == [shortcut.ENTRY_SCRIPT]
    assert os.path.exists(shortcut.ENTRY_SCRIPT)
    assert os.path.exists(shortcut.ICON_ICO)


def test_mac_app_bundle(qapp, tmp_path):
    app = shortcut._create_mac(str(tmp_path))
    assert app.endswith("Balance Streamer.app")
    with open(os.path.join(app, "Contents", "Info.plist"), "rb") as f:
        info = plistlib.load(f)
    assert info["CFBundleExecutable"] == "launch"
    launcher = os.path.join(app, "Contents", "MacOS", "launch")
    text = open(launcher, encoding="utf-8").read()
    assert "multi_balance_stream.py" in text and REPO_DIR in text
    if os.name != "nt":
        assert os.access(launcher, os.X_OK)
    if sys.platform == "darwin":  # sips is only on macOS
        assert info["CFBundleIconFile"] == "AppIcon"
        assert os.path.exists(os.path.join(app, "Contents", "Resources", "AppIcon.icns"))
    # Pressing the button again replaces the shortcut instead of failing.
    assert shortcut._create_mac(str(tmp_path)) == app


def test_linux_desktop_file(tmp_path):
    path = shortcut._create_linux(str(tmp_path))
    text = open(path, encoding="utf-8").read()
    assert "Name=Balance Streamer" in text
    assert "multi_balance_stream.py" in text


@pytest.mark.skipif(sys.platform != "win32", reason="Windows shortcuts only exist on Windows")
def test_windows_shortcut(tmp_path):
    link = shortcut.create_shortcut(desktop=str(tmp_path))
    assert link.endswith("Balance Streamer.lnk") and os.path.exists(link)
    read = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:BS_LINK); "
            "$s.TargetPath; $s.Arguments; $s.IconLocation",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "BS_LINK": link},
    )
    target, arguments, icon = read.stdout.strip().splitlines()[:3]
    assert target.lower().endswith(("pythonw.exe", "python.exe"))
    assert "multi_balance_stream.py" in arguments
    assert icon.lower().startswith(shortcut.ICON_ICO.lower())


def test_shortcut_panel_builds(window):
    panel = window.tabs.widget(0).shortcut_panel
    assert panel.btn_create.text() == "Create Desktop Shortcut"
