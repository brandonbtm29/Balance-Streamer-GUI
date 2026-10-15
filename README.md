# Balance Streamer

[![CI](https://github.com/brandonbtm29/Balance-Streamer-GUI/actions/workflows/ci.yml/badge.svg)](https://github.com/brandonbtm29/Balance-Streamer-GUI/actions/workflows/ci.yml)

A desktop app that reads several laboratory balances at once over RS-232/USB, turns the mass
readings into a live flow rate, and saves each run to Excel.

![Balance Streamer recording a run: mass and flow rate on one chart, with the readings table below](docs/screenshot.png)

*Screenshot made with simulated data: a pump running at 0.25 g/min, stepped up to 0.5 g/min at 25 minutes.*

## Why

When a pump feeds a column, the easiest honest measure of flow is the mass of liquid that comes out.
Balance Streamer logs that mass every second (or at any interval you choose) from one or more
balances, and shows the flow rate as it happens, so you can see a pump drift or a column clog while
the run is still going. It was built for column experiments in a polymer engineering lab.

## Features

- **Several balances at once**: one tab per balance, each with its own connection, chart and settings.
- **Live flow rate**: mass and flow rate (g/min) on one chart, plus a table of every reading.
- **Choice of smoothing**: a Savitzky-Golay derivative, then Mean, Median, EMA, Butterworth, or an
  Adaptive filter that matches its window to your peristaltic pump's speed and roller count.
- **Excel export**: one `.xlsx` per run with a Documentation sheet (balance, port, notes, your metadata),
  a Data sheet and a chart. File names come from a template built from tokens, for example
  `<Start Date> <Start Time> Flow rate <Material>`, where `<Material>` is a token you add yourself.
- **Auto-save and auto-stop**: save every few minutes, or stop and save when the flow drops below a
  threshold for a set time. Quick Save overwrites the last file without asking.
- **Crash protection**: every reading is also written to a backup CSV straight away. If the computer
  crashes or loses power, Recover Session brings the run back. Backups older than 30 days are deleted.
- **Tare, linear fit and pump calibration** from the side panels.
- **Dark or light theme**, and panels you can collapse and reorder.
- **One-click updates**: Settings → Application Settings → Check for Updates installs the newest
  release from GitHub and restarts.
- **Desktop shortcut**: Settings → Application Settings → Create Desktop Shortcut puts a Balance
  Streamer icon on your desktop (on Windows it opens without the console window).
- **Error log**: problems are written to `logs/balance_streamer.log` in the data folder instead of
  being skipped silently.

## Supported balances

| Balance | How it reads | Set the balance to |
|---|---|---|
| Mettler Toledo | Asks for a reading (MT-SICS `SI`) | 9600 baud, host mode |
| Ohaus Adventurer | Asks for a reading (`IP`) | 9600 baud |
| Bonvoisin | Listens to continuous output | 9600 baud, continuous print |
| Lachoi | Listens to continuous output | 9600 baud, continuous print |

All connections use 9600 baud, 8 data bits, no parity, 1 stop bit. Other balances that print a
number and a unit on each line usually work with the Bonvoisin or Lachoi setting. The app's
**Settings → Help & About** page has menu paths for setting up common balances.

## Install

You need **Python 3.11 or newer** ([python.org](https://www.python.org/downloads/)) and a USB or
RS-232 cable for each balance.

1. Download the code: **Code → Download ZIP** on GitHub, or
   ```bash
   git clone https://github.com/brandonbtm29/Balance-Streamer-GUI.git
   cd Balance-Streamer-GUI
   ```
2. Create a virtual environment and install:

   **Windows**
   ```bat
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
   **macOS**
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.txt
   ```
3. Start it by double-clicking `Launch_Windows.bat` (Windows) or `Launch_Mac.command` (macOS).
   You can also run `python multi_balance_stream.py` with the virtual environment active.
4. Optional: in **Settings → Application Settings**, press **Create Desktop Shortcut**. From then on
   you can start the app from the Balance Streamer icon on your desktop. On a Mac it is a small app
   you can also drag to the Dock or Applications.

If your computer doesn't list the balance's port, install the driver for your USB-serial adapter
(for example FTDI).

## Updating

Open **Settings → Application Settings** and press **Check for Updates**. If a newer release is out,
**Update and Restart** saves your tabs, downloads it, reinstalls the requirements and restarts. A
recording in progress stops; its data stays in the backup file for Recover Session.

This works when the app was installed with `git clone` (step 1 above) and needs git on the computer.
It only moves to published releases, never to unfinished work, and it won't overwrite files you
changed in the app's folder. If installing the new requirements fails, the app goes back to the
version you had. Copies downloaded as a ZIP, and standalone builds, show a link to the
[release page](https://github.com/brandonbtm29/Balance-Streamer-GUI/releases/latest) instead.

Version 1.0.0 has no update button: update it once by running `git pull` in the app's folder, then
`pip install -r requirements.txt` with the virtual environment's Python.

## Using it

1. Plug in the balance and set it up as in the table above.
2. In the balance tab, pick the **Balance Brand** and **COM Port** (Refresh Ports if it's missing),
   then **Connect**.
3. Press **▶** to start recording. Press it again to stop.
4. Press the Excel button to save, or set up **Auto-Save Settings** so it saves for you.
5. Add a tab for each extra balance with **Tab Management → Add Tab**.

The buttons across the top of each balance tab, left to right (hover over one to see its name):

| Button | What it does |
|---|---|
| Start / Stop Recording | Start or stop logging readings |
| Clear Data | Clear the readings in this tab and start a new run |
| Save to Excel | Save the run to Excel (asks where) |
| Quick Save | Overwrite the last saved file without asking |
| Tare Balance | Send a tare command (`T`) to the balance |
| Save Graph PNG | Save the chart as an image |
| Recover Session | Restore a run from the backup files |

## Where files go

The app keeps its code and its data apart:

- **Data folder**: `~/SyncThing/UAkron Playground/Balance Streamer Application/` by default.
  The app works inside this folder, so exports land in `Data/` and backups in `Data Backups/`.
  Set the `UAKRON_APP_DATA_DIR` environment variable to use another folder (or `UAKRON_DATA_DIR`
  to move the parent folder).
- **Settings** (`config.json`): in the app's own folder by default. In
  **Settings → Application Settings → Settings Folder** you can move them, for example into the data
  folder so several computers share them. `UAKRON_SETTINGS_DIR` overrides this.
- **Log**: `logs/balance_streamer.log` in the data folder (three files of up to 1 MB are kept).
  If `config.json` can't be read, it is kept as `config.json.unreadable` and the app starts with
  default settings.

Neither data nor settings are ever stored in the repository; both are in `.gitignore`.

## Build a standalone app

```bash
python build_app.py
```

This uses PyInstaller to make `dist/Balance_Streamer/`, which runs without Python installed.
Build on the system you want to run it on (Windows for an `.exe`, macOS for a Mac app).

## Good to know

- The flow rate assumes the liquid is collected on the balance. It is reported in g/min; convert
  to mL/min with your liquid's density.
- A balance tab only records while you press ▶. Being connected isn't enough.
- Closing a tab forgets its saved connection settings.
- The app only goes online when you press **Check for Updates** (to ask GitHub for the latest release).

## Development

```bash
python -m pip install -e ".[dev]"
pytest              # headless Qt tests: parsers, flow rates, export, errors, updater
ruff check .
ruff format .
python -m balance_streamer   # run from source
```

The code is in the `balance_streamer` package:

| Module | What's in it |
|---|---|
| `app.py` | `main()`: moves into the data folder, sets up logging and the theme, opens the window |
| `paths.py` | Where data and settings live |
| `main_window.py` | The window: a Settings tab plus one tab per balance |
| `balance_tab.py` | One balance tab (layout, connection, recording, chart and table) |
| `flow.py`, `export.py`, `recovery.py`, `tab_config.py` | The balance tab's flow maths, saving, crash recovery and saved tab settings |
| `serial_worker.py`, `parsers.py` | Reading a balance in a background thread and decoding its lines |
| `settings_tab.py`, `widgets.py` | The Settings tab and small shared widgets |
| `updater.py`, `update_panel.py` | Checking GitHub and updating a git copy |
| `shortcut.py`, `shortcut_panel.py` | Create Desktop Shortcut (Windows .lnk, Mac .app, Linux .desktop) |
| `theme.py`, `logs.py` | Dark/light theme and the error log |

`multi_balance_stream.py` only starts the app; it stays for the launchers and `build_app.py`.
`settings_location.py` is shared, unchanged, with the other UAkron lab apps.

The tests point the app at a temporary data folder, so they never touch your real data. CI runs
them on Windows, macOS and Linux with Python 3.11 to 3.13, and scans the history for secrets.

The version number lives in one place: `__version__` in `balance_streamer/__init__.py`. Changes are
listed in [CHANGELOG.md](CHANGELOG.md). Updates find new versions through GitHub releases, so each
release needs an `vX.Y.Z` tag and a published release.

## How this was built

Balance Streamer is written and maintained by Brandon T. McReynolds with the help of AI coding
assistants. Earlier versions (before October 10, 2026) were co-developed with Google Gemini in
Antigravity. Later versions were co-developed with Claude (Anthropic); those commits list Claude as a
co-author. Brandon directs the work, reviews and tests the changes, and is responsible for the
project.

## License

[MIT](LICENSE)
