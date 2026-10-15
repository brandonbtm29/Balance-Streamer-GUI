@echo off
rem Starts Balance Streamer without a console window (pythonw), using this folder's .venv.
rem If the app can't start it shows a message and writes startup-error.log in this folder.
cd /d "%~dp0"
set "PYW=pythonw"
if exist ".venv\Scripts\pythonw.exe" set "PYW=.venv\Scripts\pythonw.exe"
start "" "%PYW%" multi_balance_stream.py
