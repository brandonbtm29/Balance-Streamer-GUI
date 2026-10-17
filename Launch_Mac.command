#!/bin/bash
# Runs Balance Streamer with its messages shown in this Terminal window (for troubleshooting).
# For everyday use, double-click "Balance Streamer.app" in this folder, or the desktop shortcut:
# they start the app without a Terminal window.
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY="python3"; fi
"$PY" multi_balance_stream.py || { echo; echo "The app stopped with an error. Copy the messages above when asking for help."; echo "If a module is missing, double-click Setup_Mac.command to install what it needs."; read -r -p "Press Enter to close"; }
