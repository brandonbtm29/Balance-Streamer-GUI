@echo off
rem Double-click launcher for Windows. Starts Balance Streamer without leaving a console window open.
rem (The desktop shortcut the app makes opens it without any console window at all.)
rem The first time, it sets the app up: it creates this folder's own Python environment (.venv) and
rem installs everything the app needs. Setup_Windows.bat does the same, to repair or reinstall.
rem For troubleshooting, Troubleshoot_Windows.bat runs the app with its messages shown.
cd /d "%~dp0"

rem First run: there is no .venv yet, so make it and install the app (the same steps as Setup_Windows.bat).
if not exist ".venv\Scripts\python.exe" (
  echo Setting up Balance Streamer for the first time. This takes a minute or two...
  echo.
  echo Creating .venv ...
  py -3.12 -m venv .venv 2>nul || py -3 -m venv .venv 2>nul || python -m venv .venv
  if not exist ".venv\Scripts\python.exe" goto nopython
  ".venv\Scripts\python.exe" -c "import sys; sys.exit(sys.version_info < (3, 11))" || goto oldpython
  ".venv\Scripts\python.exe" -m pip install --upgrade pip || goto failed
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto failed
  echo.
  echo Setup finished. Starting Balance Streamer...
)

set "PY=python"
set "PYW=pythonw"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if exist ".venv\Scripts\pythonw.exe" set "PYW=.venv\Scripts\pythonw.exe"

rem Quick check that the app can start. If not, show why and keep this window open.
"%PY%" -c "import PyQt6.QtWidgets, serial, matplotlib, scipy, openpyxl" 2>nul
if errorlevel 1 (
  echo The app can't start: its Python packages are missing or broken.
  echo.
  "%PY%" -c "import PyQt6.QtWidgets, serial, matplotlib, scipy, openpyxl"
  echo.
  echo To install what it needs, double-click Setup_Windows.bat.
  pause
  exit /b 1
)

rem pythonw runs the app without a console; errors from here on go to logs\balance_streamer.log in the data folder.
start "" "%PYW%" multi_balance_stream.py
exit /b 0

:nopython
echo.
echo Python 3.11 or newer isn't installed, or isn't on PATH.
echo Install it from https://www.python.org/downloads/ (tick "Add python.exe to PATH"), then run this again.
pause
exit /b 1

:oldpython
echo.
echo The .venv folder uses a Python older than 3.11. Delete the .venv folder, install a newer
echo Python from https://www.python.org/downloads/, then run this again.
pause
exit /b 1

:failed
echo.
echo Setup didn't finish. Copy the messages above when asking for help.
echo To try again, double-click Setup_Windows.bat.
pause
exit /b 1
