"""Put a "Balance Streamer" shortcut on the desktop.

* Windows: a .lnk shortcut that starts the app with pythonw.exe (no console window)
  and shows the balance icon. Made with Windows' own WScript.Shell through PowerShell.
* macOS: a small "Balance Streamer.app" that starts the app with this copy's Python.
  It can be dragged to the Dock or Applications.
* Linux: a .desktop launcher.

The shortcut points at this folder and its Python, so it keeps working after updates.
Creating it again replaces the old one. When the app starts it refreshes an existing
shortcut after an update (so the icon and paths stay current) and, the first time on a
computer, offers to create one. That per-computer state lives in local_state.json in the
app folder (gitignored), not in config.json, which may be shared between computers.
"""

import json
import logging
import os
import plistlib
import shlex
import subprocess
import sys

from . import __version__
from .paths import APP_DIR, ICON_FILE, REPO_DIR

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


def shortcut_path(desktop):
    """Where this platform's shortcut lives on the given desktop."""
    if sys.platform == "win32":
        return os.path.join(desktop, APP_NAME + ".lnk")
    if sys.platform == "darwin":
        return os.path.join(desktop, APP_NAME + ".app")
    return os.path.join(desktop, "balance-streamer.desktop")


def create_shortcut(desktop=None):
    """Create (or replace) the desktop shortcut and return its path."""
    desktop = desktop or desktop_folder()
    if sys.platform == "win32":
        path = _create_windows(desktop)
    elif sys.platform == "darwin":
        path = _create_mac(desktop)
    else:
        path = _create_linux(desktop)
    save_state(shortcut_version=__version__, shortcut_offered=True)
    return path


# --- what to do at startup ------------------------------------------------------------------

STATE_FILE = os.path.join(APP_DIR, "local_state.json")


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def save_state(**changes):
    state = load_state()
    state.update(changes)
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except OSError:
        log.warning("Couldn't save %s", STATE_FILE, exc_info=True)


def startup_action(exists, state, version=__version__):
    """'refresh' an outdated shortcut, 'offer' to make one the first time, or 'nothing'."""
    if exists:
        return "refresh" if state.get("shortcut_version") != version else "nothing"
    if state.get("shortcut_offered"):
        return "nothing"  # already asked on this computer, or the user deleted the shortcut
    return "offer"


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


def make_icns(dest):
    """Write the balance icon as a macOS .icns file (with Pillow). Returns True if it worked."""
    if not os.path.exists(ICON_ICO):
        return False
    try:
        from PIL import Image

        with Image.open(ICON_ICO) as im:
            im.size = max(im.ico.sizes())  # use the largest picture in the .ico
            im.load()
            im.save(dest, format="ICNS")
        return True
    except (OSError, ValueError, AttributeError):  # an icon is nice to have; the shortcut works without it
        log.warning("Couldn't make the shortcut icon", exc_info=True)
        return False


# Shows a macOS alert: MAC_ALERT "title" "message"
MAC_ALERT = (
    "osascript -e 'on run argv' "
    "-e 'display alert (item 1 of argv) message (item 2 of argv) as critical' -e 'end run'"
)


def _create_mac(desktop):
    program, args = launch_command()
    app = os.path.join(desktop, APP_NAME + ".app")
    # Files are rewritten in place rather than deleting the app first, because the app
    # may be running from this very shortcut when it refreshes it after an update.
    macos = os.path.join(app, "Contents", "MacOS")
    resources = os.path.join(app, "Contents", "Resources")
    os.makedirs(macos, exist_ok=True)
    os.makedirs(resources, exist_ok=True)

    launcher = os.path.join(macos, "launch")
    command = " ".join(shlex.quote(part) for part in [program, *args])
    with open(launcher, "w", encoding="utf-8") as f:
        f.write(
            "#!/bin/bash\n"
            '# Made by Balance Streamer\'s "Create Desktop Shortcut" button.\n'
            f"if [ ! -x {shlex.quote(program)} ]; then\n"
            f'  {MAC_ALERT} "Balance Streamer can\'t start" '
            f"{shlex.quote('It was moved or its Python is missing. Open the app folder and run Launch_Mac.command, then press Create Desktop Shortcut again.')}\n"
            "  exit 1\n"
            "fi\n"
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
    if make_icns(os.path.join(resources, "AppIcon.icns")):
        info["CFBundleIconFile"] = "AppIcon"
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
