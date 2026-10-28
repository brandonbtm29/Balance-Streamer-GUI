@echo off
rem Runs Balance Streamer with its messages shown in this console window (for troubleshooting).
rem For everyday use, double-click Launch_Windows.bat or the desktop shortcut instead:
rem they start the app without a console window.
cd /d "%~dp0"
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
echo Starting Balance Streamer. Its messages appear in this window; keep it open while the app runs.
echo.
"%PY%" multi_balance_stream.py
if errorlevel 1 (
  echo.
  echo The app stopped with an error. Copy the messages above when asking for help.
  echo If a module is missing, double-click Setup_Windows.bat to install what it needs.
  pause
  exit /b 1
)
exit /b 0
