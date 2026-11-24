"""Where the app's data and settings live.

Data (exports, backups, logs) lives in the data folder: ``~/SyncThing/Balance Streamer
Application`` on computers that share it through Syncthing, ``Documents/Balance Streamer``
everywhere else (see :func:`default_data_dir`). At startup the app moves into it (see
:func:`enter_data_dir`), so relative paths like "Data/" land there. Override with
UAKRON_APP_DATA_DIR (this app) or UAKRON_DATA_DIR (data root).

Settings (config.json) live in the app folder by default, gitignored. The "Settings
Folder" option (settings_location.py) can point them at a synced folder instead,
e.g. "Settings" inside the data folder.
"""

import os
import platform
import re
import sys

# The repository (or install) folder: the parent of this package.
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
import settings_location  # noqa: E402  (shared helper at the repository root)

DATA_FOLDER_NAME = "Balance Streamer Application"  # the app's Syncthing folder, in ~/SyncThing
LOCAL_FOLDER_NAME = "Balance Streamer"  # in Documents, on a computer without that Syncthing folder
OLD_SYNC_FOLDER = "UAkron Playground"  # the SyncThing folder all the lab apps shared before Nov 2026
SYNC_DATA_DIR = os.path.join(os.path.expanduser("~"), "SyncThing", DATA_FOLDER_NAME)


def documents_folder(home=None):
    """The user's Documents folder. On Windows, where it really is (it can be moved, e.g. to OneDrive)."""
    if home is None and sys.platform == "win32":
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "Personal")
            path = os.path.expandvars(value)
            if os.path.isabs(path):
                return path
        except OSError:
            pass
    return os.path.join(home or os.path.expanduser("~"), "Documents")


def default_data_dir(home=None):
    """Where the data goes when no environment variable says otherwise.

    ``~/SyncThing/Balance Streamer Application`` if that folder exists: the computers that share
    their data through Syncthing. A computer that only has the old shared folder
    (``~/SyncThing/UAkron Playground/...``) keeps using that until Syncthing brings the new one.
    Every other computer uses ``Documents/Balance Streamer``. To share the data with Syncthing,
    share a folder named "Balance Streamer Application" inside ``~/SyncThing`` on each computer;
    the app uses it from its next start.
    """
    sync = os.path.join(home or os.path.expanduser("~"), "SyncThing")
    new = os.path.join(sync, DATA_FOLDER_NAME)
    old = os.path.join(sync, OLD_SYNC_FOLDER, DATA_FOLDER_NAME)
    if os.path.isdir(new):
        return new
    if os.path.isdir(old):
        return old
    return os.path.join(documents_folder(home), LOCAL_FOLDER_NAME)


DATA_DIR = os.environ.get("UAKRON_APP_DATA_DIR") or (
    os.path.join(os.environ["UAKRON_DATA_DIR"], DATA_FOLDER_NAME)
    if os.environ.get("UAKRON_DATA_DIR")
    else default_data_dir()
)
APP_DIR = settings_location.app_folder(REPO_DIR)
CONFIG_DIR = settings_location.resolve(APP_DIR, DATA_DIR)
SETTINGS_FILES = ["config.json"]
ICON_FILE = os.path.join(REPO_DIR, "assets", "Analytical Balance.ico")


def computer_folder_name():
    """This computer's name, safe as a folder name (e.g. "Lab-PC"). Used to keep files that
    each computer writes, like the log, apart inside the shared (SyncThing) data folder."""
    name = re.sub(r"[^A-Za-z0-9._-]+", "-", platform.node().split(".")[0]).strip("-.")
    return name[:40] or "this-computer"


def enter_data_dir():
    """Make the data folder the working directory (created if missing)."""
    sys.argv[0] = os.path.abspath(sys.argv[0])  # keeps "Restart" working after chdir
    os.makedirs(DATA_DIR, exist_ok=True)
    os.chdir(DATA_DIR)
