#!/bin/bash
# Double-click launcher for macOS. Data is saved to ~/SyncThing/UAkron Playground/Balance Streamer Application
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"
if [ -x ".venv/bin/python" ]; then PY=".venv/bin/python"; else PY="python3"; fi
"$PY" multi_balance_stream.py || { echo; echo "The app stopped with an error. Copy the messages above when asking for help."; read -r -p "Press Enter to close"; }
