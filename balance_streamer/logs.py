"""Write problems to logs/<computer>/balance_streamer.log in the data folder.

Each computer has its own folder under logs/, because the data folder is shared through
SyncThing: two computers writing the same log file produced sync-conflict copies.

This uses crash_log.py, the same file as in the other UAkron lab apps. It keeps the log
small (three files of 1 MB), logs errors nobody caught, also from background threads such
as the serial readers, and shows them in a dialog instead of closing the app: PyQt6
otherwise ends the program when an error escapes a button handler or timer, which would
stop a recording. A hard crash (in a driver or in Qt itself) is written to
balance_streamer.fatal.log in the same folder.

On Windows, Python's crash reporter also writes some errors that Windows itself handles and
that don't stop the app (for example "Windows fatal exception: code 0x8001010d", a COM
call refused while the window was busy). So when the app closes normally it adds an
"exited normally" line to the fatal log: a report followed by that line was not a crash.
"""

import os
import time

import crash_log

from . import __version__
from .paths import DATA_DIR, computer_folder_name

LOG_NAME = "balance_streamer"
LOG_DIR = os.path.join(DATA_DIR, "logs", computer_folder_name())


def setup_logging():
    """Start the log file and the error handlers. Returns the log file's path. Safe to call twice.

    If the data folder can't be written to (for example a missing or read-only SyncThing
    folder), the log goes to the per-user log folder instead, so a start-up error still
    leaves a trace. Returns None only if neither folder can be written to.
    """
    return crash_log.setup(LOG_NAME, LOG_DIR, __version__) or crash_log.setup(
        LOG_NAME, crash_log.user_log_dir("Balance Streamer"), __version__
    )


def note_clean_exit():
    """Mark in the fatal log that the app closed normally (see the module docstring)."""
    path = crash_log.log_path()
    if not path:
        return
    try:
        with open(os.path.join(os.path.dirname(path), f"{LOG_NAME}.fatal.log"), "a", encoding="utf-8") as f:
            f.write(
                f"--- {LOG_NAME} {__version__} exited normally {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n"
            )
    except OSError:
        pass  # only a courtesy note; never let it stop the app from closing
