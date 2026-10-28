"""Write problems to logs/balance_streamer.log in the data folder.

This uses crash_log.py, the same file as in the other UAkron lab apps. It keeps the log
small (three files of 1 MB), logs errors nobody caught, also from background threads such
as the serial readers, and shows them in a dialog instead of closing the app: PyQt6
otherwise ends the program when an error escapes a button handler or timer, which would
stop a recording. A hard crash (in a driver or in Qt itself) is written to
logs/balance_streamer.fatal.log.
"""

import os

import crash_log

from . import __version__
from .paths import DATA_DIR

LOG_NAME = "balance_streamer"
LOG_DIR = os.path.join(DATA_DIR, "logs")


def setup_logging():
    """Start the log file and the error handlers. Returns the log file's path. Safe to call twice.

    If the data folder can't be written to (for example a missing or read-only SyncThing
    folder), the log goes to the per-user log folder instead, so a start-up error still
    leaves a trace. Returns None only if neither folder can be written to.
    """
    return crash_log.setup(LOG_NAME, LOG_DIR, __version__) or crash_log.setup(
        LOG_NAME, crash_log.user_log_dir("Balance Streamer"), __version__
    )
