"""Start Balance Streamer.

The code lives in the balance_streamer package; this file stays so the launchers,
build_app.py and existing shortcuts keep working.

The launchers start the app without a terminal window, so if it can't even start
(for example a missing package after a failed install), the reason is shown in a
message box and written to startup-error.log next to this file.
"""

import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))


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


def report_startup_error():
    details = traceback.format_exc()
    log_path = os.path.join(HERE, "startup-error.log")
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            f.write(details)
    except OSError:
        log_path = "(couldn't write startup-error.log)"
    if sys.stderr is not None:
        print(details, file=sys.stderr)
    last_line = details.strip().splitlines()[-1] if details.strip() else "Unknown error"
    _show_message(
        "Balance Streamer couldn't start",
        f"{last_line}\n\nDetails were saved to:\n{log_path}\n\n"
        "If a package is missing, reinstall the requirements (see Install in the README).",
    )


if __name__ == "__main__":
    try:
        from balance_streamer.app import main

        main()
    except Exception:
        report_startup_error()
        sys.exit(1)
