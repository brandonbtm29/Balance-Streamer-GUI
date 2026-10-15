"""Where the app's data and settings live.

Code lives in GitHub Projects/UAkron/<repo>; data (exports, backups, logs) lives in
SyncThing. At startup the app moves into the data folder (see :func:`enter_data_dir`),
so relative paths like "Data/" land there. Override with UAKRON_APP_DATA_DIR (this
app) or UAKRON_DATA_DIR (data root).

Settings (config.json) live in the app folder by default, gitignored. The "Settings
Folder" option (settings_location.py) can point them at a synced folder instead,
e.g. "Settings" inside the data folder.
"""

import os
import sys

# The repository (or install) folder: the parent of this package.
REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_DIR not in sys.path:
    sys.path.insert(0, REPO_DIR)
import settings_location  # noqa: E402  (shared helper at the repository root)

DATA_DIR = os.environ.get("UAKRON_APP_DATA_DIR") or os.path.join(
    os.environ.get("UAKRON_DATA_DIR")
    or os.path.join(os.path.expanduser("~"), "SyncThing", "UAkron Playground"),
    "Balance Streamer Application",
)
APP_DIR = settings_location.app_folder(REPO_DIR)
CONFIG_DIR = settings_location.resolve(APP_DIR, DATA_DIR)
SETTINGS_FILES = ["config.json"]
ICON_FILE = os.path.join(REPO_DIR, "assets", "Analytical Balance.ico")


def enter_data_dir():
    """Make the data folder the working directory (created if missing)."""
    sys.argv[0] = os.path.abspath(sys.argv[0])  # keeps "Restart" working after chdir
    os.makedirs(DATA_DIR, exist_ok=True)
    os.chdir(DATA_DIR)
