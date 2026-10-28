#!/bin/bash
# Double-click launcher for macOS. Starts Balance Streamer in the background and closes this
# Terminal window. Errors after start-up go to logs/balance_streamer.log in the data folder.
# The first time, it sets the app up: it creates this folder's own Python environment (.venv) and
# installs everything the app needs. Setup_Mac.command does the same, to repair or reinstall.
# For troubleshooting, Troubleshoot_Mac.command runs the app with its messages shown in Terminal.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR" || exit 1
fail() { echo; echo "$1"; read -r -p "Press Enter to close"; exit 1; }
new_enough() { "$1" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; }

# First run: there is no .venv yet, so make it and install the app (the same steps as Setup_Mac.command).
if [ ! -x ".venv/bin/python" ]; then
  echo "Setting up Balance Streamer for the first time. This takes a minute or two..."
  echo
  PYTHON=""
  for p in python3.12 python3.13 python3.11 python3; do
    if command -v "$p" >/dev/null && new_enough "$p"; then PYTHON="$p"; break; fi
  done
  [ -n "$PYTHON" ] || fail "Python 3.11 or newer isn't installed. Get it from https://www.python.org/downloads/ and run this again."
  echo "Creating .venv with $PYTHON ..."
  "$PYTHON" -m venv .venv || fail "Couldn't create the .venv folder."
  FAILED="Setup didn't finish. Copy the messages above when asking for help. To try again, double-click Setup_Mac.command."
  .venv/bin/python -m pip install --upgrade pip || fail "$FAILED"
  .venv/bin/python -m pip install -r requirements.txt || fail "$FAILED"
  echo
  echo "Setup finished. Starting Balance Streamer..."
fi
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY="python3"; fi

# Quick check here, so missing packages show an error instead of nothing happening.
if ! "$PY" -c "import PyQt6.QtWidgets, serial, matplotlib, scipy, openpyxl"; then
  echo
  echo "The app could not start. Copy the messages above when asking for help."
  echo "To install what it needs, double-click Setup_Mac.command."
  read -r -p "Press Enter to close"
  exit 1
fi

# Start the app in its own session (so closing this window doesn't stop it), then ask Terminal
# to close this window once the script has finished.
"$PY" - "$PY" "$(tty)" <<'PYEOF'
import subprocess, sys
python, tty = sys.argv[1], sys.argv[2]
quiet = dict(stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
subprocess.Popen([python, "multi_balance_stream.py"], **quiet)
script = (
    "delay 1\n"
    'tell application "Terminal"\n'
    "  repeat with w in (every window)\n"
    f'    if tty of selected tab of w is "{tty}" then close w\n'
    "  end repeat\n"
    "end tell"
)
try:
    subprocess.Popen(["osascript", "-e", script], **quiet)
except OSError:
    pass
PYEOF
exit 0
