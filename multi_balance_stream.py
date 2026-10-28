"""Start Balance Streamer.

The code lives in the balance_streamer package; this file stays so the launchers,
build_app.py and existing shortcuts keep working.

The launchers start the app without a terminal window, so the log file is set up
first (logs/balance_streamer.log in the data folder, see balance_streamer/logs.py).
If the app can't even start (for example a missing package after a failed install),
the reason is written to that log and shown in a message box.
"""

import logging
import sys
import traceback


def _show_message(title, text):
    """A native message box that works before Qt is available."""
    try:
        if sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(None, text, title, 0x10)  # MB_ICONERROR
        elif sys.platform == "darwin":
            import subprocess

            subprocess.run(  # noqa: S603 - fixed AppleScript; the text is passed as an argument
                [
                    "/usr/bin/osascript",
                    "-e",
                    "on run argv",
                    "-e",
                    "display alert (item 1 of argv) message (item 2 of argv) as critical",
                    "-e",
                    "end run",
                    title,
                    text,
                ],
                timeout=600,
            )
    except Exception:  # noqa: S110 - nothing more we can do; the log file still has the details
        pass


def _log_path():
    """The log file crash_log.py writes to, or None if logging couldn't be set up."""
    try:
        import crash_log

        return crash_log.log_path()
    except Exception:  # even crash_log itself may be what failed to load
        return None


def report_startup_error():
    """Log why the app couldn't start and say so in a message box (there may be no console)."""
    details = traceback.format_exc()
    log_path = _log_path()
    if log_path:  # also printed to the console, if there is one
        logging.getLogger("balance_streamer").critical("Balance Streamer couldn't start", exc_info=True)
    elif sys.stderr is not None:
        print(details, file=sys.stderr)
    last_line = details.strip().splitlines()[-1] if details.strip() else "Unknown error"
    where = (
        f"Details were saved to:\n{log_path}" if log_path else "The details couldn't be saved to a log file."
    )
    setup = "Setup_Windows.bat" if sys.platform == "win32" else "Setup_Mac.command"
    _show_message(
        "Balance Streamer couldn't start",
        f"{last_line}\n\n{where}\n\n"
        f"If a package is missing, double-click {setup} in the app's folder to reinstall what it needs.",
    )


if __name__ == "__main__":
    try:
        from balance_streamer.logs import setup_logging

        setup_logging()  # before the rest is imported, so an import error is logged too
        from balance_streamer.app import main

        main()
    except Exception:
        report_startup_error()
        sys.exit(1)
