"""Write problems to logs/balance_streamer.log in the data folder.

The app used to skip over many errors without a trace. They are now written to a
log file (kept small: three files of 1 MB), so a failed backup or a balance that
stopped answering can be found afterwards.
"""

import logging
import logging.handlers
import os
import sys
import time

LOG_DIR = "logs"  # relative to the data folder, which is the working directory
LOG_FILE = "balance_streamer.log"


def setup_logging(level=logging.INFO):
    """Send log messages to the log file (and the console). Safe to call twice."""
    root = logging.getLogger()
    if any(getattr(h, "_balance_streamer", False) for h in root.handlers):
        return
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        os.path.join(LOG_DIR, LOG_FILE), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
    )
    handler._balance_streamer = True
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    if sys.stderr is not None:  # pythonw (the desktop shortcut on Windows) has no console
        console = logging.StreamHandler()
        console._balance_streamer = True
        console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        root.addHandler(console)
    root.setLevel(level)


def install_excepthook():
    """Log errors nobody caught and tell the user, instead of closing the app.

    PyQt6 ends the program when an error escapes a button handler or timer. During a
    recording that would stop logging, so the error is shown and recording goes on.
    """

    last_shown = [0.0]

    def hook(exc_type, exc, tb):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc, tb)
            return
        logging.getLogger("balance_streamer").critical("Unexpected error", exc_info=(exc_type, exc, tb))
        if time.monotonic() - last_shown[0] < 60:  # an error in a timer would repeat every tick
            return
        last_shown[0] = time.monotonic()
        try:
            from PyQt6.QtWidgets import QApplication, QMessageBox

            if QApplication.instance() is not None:
                QMessageBox.warning(
                    None,
                    "Unexpected error",
                    f"Something went wrong: {exc}\n\n"
                    f"Details were saved to {os.path.abspath(os.path.join(LOG_DIR, LOG_FILE))}.",
                )
        except Exception:  # noqa: S110 - never let the error handler itself crash the app
            pass

    sys.excepthook = hook
