"""Put a "Balance Streamer" shortcut on the desktop.

* Windows: a .lnk shortcut that starts the app with pythonw.exe (no console window)
  and shows the balance icon. Made with Windows' own WScript.Shell through PowerShell.
* macOS: a small "Balance Streamer.app" that starts the app with this copy's Python.
  It can be dragged to the Dock or Applications.
* Linux: a .desktop launcher.

The shortcut points at this folder and its Python, so it keeps working after updates.
Creating it again replaces the old one.
"""

import logging
import os
import plistlib
import shlex
import shutil
import subprocess
import sys
import tempfile

from . import __version__
from .paths import ICON_FILE, REPO_DIR

log = logging.getLogger(__name__)

APP_NAME = "Balance Streamer"
ICON_ICO = ICON_FILE
ENTRY_SCRIPT = os.path.join(REPO_DIR, "multi_balance_stream.py")


class ShortcutError(Exception):
    """A problem with a plain-language message for the user."""


def launch_command():
    """(program, arguments) that start this copy of the app without a terminal."""
    if getattr(sys, "frozen", False):  # PyInstaller build: the executable is the app
        return sys.executable, []
    python = sys.executable
    if sys.platform == "win32":
        pythonw = os.path.join(os.path.dirname(python), "pythonw.exe")
        if os.path.exists(pythonw):
            python = pythonw
    return python, [ENTRY_SCRIPT]


def desktop_folder():
    """The user's desktop, including a desktop moved into OneDrive on Windows."""
    if sys.platform == "win32":
        result = _powershell("[Environment]::GetFolderPath('Desktop')")
        path = result.stdout.strip()
        if result.returncode == 0 and path:
            return path
    path = os.path.join(os.path.expanduser("~"), "Desktop")
    if not os.path.isdir(path):
        raise ShortcutError(f"Couldn't find your desktop folder ({path}).")
    return path


def create_shortcut(desktop=None):
    """Create (or replace) the desktop shortcut and return its path."""
    desktop = desktop or desktop_folder()
    if sys.platform == "win32":
        return _create_windows(desktop)
    if sys.platform == "darwin":
        return _create_mac(desktop)
    return _create_linux(desktop)


# --- Windows ------------------------------------------------------------------------------


def _powershell(script, env=None):
    kwargs = {"creationflags": 0x08000000} if os.name == "nt" else {}  # no console window
    return subprocess.run(  # noqa: S603 - fixed script; values are passed in environment variables
        ["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        timeout=60,
        env={**os.environ, **(env or {})},
        **kwargs,
    )


_LNK_SCRIPT = """
$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:BS_LINK)
$s.TargetPath = $env:BS_TARGET
$s.Arguments = $env:BS_ARGS
$s.WorkingDirectory = $env:BS_WORKDIR
$s.IconLocation = $env:BS_ICON
$s.Description = $env:BS_DESCRIPTION
$s.Save()
"""


def _create_windows(desktop):
    program, args = launch_command()
    link = os.path.join(desktop, APP_NAME + ".lnk")
    icon = ICON_ICO if os.path.exists(ICON_ICO) else program
    result = _powershell(
        _LNK_SCRIPT,
        env={
            "BS_LINK": link,
            "BS_TARGET": program,
            "BS_ARGS": subprocess.list2cmdline(args),
            "BS_WORKDIR": REPO_DIR,
            "BS_ICON": icon + ",0",
            "BS_DESCRIPTION": "Stream lab balances and log flow rates",
        },
    )
    if result.returncode != 0 or not os.path.exists(link):
        raise ShortcutError(
            "Windows couldn't create the shortcut:\n" + (result.stderr or result.stdout).strip()
        )
    return link


# --- macOS --------------------------------------------------------------------------------


def _mac_icns(resources):
    """Turn the .ico into AppIcon.icns with Qt and macOS's sips. Returns the file name or None."""
    if not os.path.exists(ICON_ICO) or shutil.which("sips") is None:
        return None
    try:
        from PyQt6.QtGui import QIcon

        with tempfile.TemporaryDirectory() as tmp:
            png = os.path.join(tmp, "icon.png")
            if not QIcon(ICON_ICO).pixmap(256, 256).save(png, "PNG"):
                return None
            out = os.path.join(resources, "AppIcon.icns")
            done = subprocess.run(  # noqa: S603, S607 - macOS's own image tool, fixed arguments
                ["sips", "-s", "format", "icns", png, "--out", out], capture_output=True, timeout=60
            )
            return "AppIcon" if done.returncode == 0 and os.path.exists(out) else None
    except Exception:  # an icon is nice to have; the shortcut works without it
        log.warning("Couldn't make the shortcut icon", exc_info=True)
        return None


def _create_mac(desktop):
    program, args = launch_command()
    app = os.path.join(desktop, APP_NAME + ".app")
    if os.path.exists(app):
        shutil.rmtree(app)
    macos = os.path.join(app, "Contents", "MacOS")
    resources = os.path.join(app, "Contents", "Resources")
    os.makedirs(macos)
    os.makedirs(resources)

    launcher = os.path.join(macos, "launch")
    command = " ".join(shlex.quote(part) for part in [program, *args])
    with open(launcher, "w", encoding="utf-8") as f:
        f.write(
            "#!/bin/bash\n"
            '# Made by Balance Streamer\'s "Create Desktop Shortcut" button.\n'
            f"cd {shlex.quote(REPO_DIR)} || exit 1\n"
            f'exec {command} "$@"\n'
        )
    os.chmod(launcher, 0o755)

    info = {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "io.github.brandonbtm29.balance-streamer",
        "CFBundleExecutable": "launch",
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": __version__,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
    }
    icon = _mac_icns(resources)
    if icon:
        info["CFBundleIconFile"] = icon
    with open(os.path.join(app, "Contents", "Info.plist"), "wb") as f:
        plistlib.dump(info, f)
    os.utime(app)  # nudge Finder to pick up the new icon
    return app


# --- Linux --------------------------------------------------------------------------------


def _create_linux(desktop):
    program, args = launch_command()
    path = os.path.join(desktop, "balance-streamer.desktop")
    command = " ".join(shlex.quote(part) for part in [program, *args])
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            "[Desktop Entry]\n"
            "Type=Application\n"
            f"Name={APP_NAME}\n"
            "Comment=Stream lab balances and log flow rates\n"
            f"Exec={command}\n"
            f"Path={REPO_DIR}\n"
            f"Icon={ICON_ICO}\n"
            "Terminal=false\n"
        )
    os.chmod(path, 0o755)
    return path
