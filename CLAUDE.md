# Balance Streamer Application

PyQt6 desktop app that streams several lab balances at once over RS-232/USB serial, computes live flow rates from mass, and exports `.xlsx` with embedded charts. Part of Brandon's UAkron lab workspace (shared conventions in `../CLAUDE.md` when the repos are cloned side by side in `GitHub Projects/UAkron/`). GitHub: `brandonbtm29/Balance-Streamer-GUI`.

## Run / build / test
- Install: `pip install -r requirements.txt` (installs this folder from `pyproject.toml`, plus PyInstaller). Dev tools: `pip install -e ".[dev]"`.
- Run: `python multi_balance_stream.py` (or the launchers, `python -m balance_streamer`, or the `balance-streamer` command once installed)
- Build executable: `python build_app.py` → `dist/Balance_Streamer/` (PyInstaller `--onedir`, excludes PyQt5/PySide6)
- Tests: `python -m pytest` (headless Qt; `tests/conftest.py` points the data and settings folders at a temp folder, so tests never touch SyncThing)
- Lint/format: `ruff check .` and `ruff format .` (config in `pyproject.toml`; `settings_location.py` is excluded because it must stay identical across the UAkron repos)
- CI (`.github/workflows/ci.yml`): ruff + pytest on Windows/macOS/Linux, Python 3.11-3.13, plus a gitleaks scan of the whole history. Check it with `gh run list`.
- Version: `__version__` in `balance_streamer/__init__.py` is the only copy. The in-app updater compares it with the latest GitHub release, so every release needs a `vX.Y.Z` tag and a published release (not a draft or pre-release). To release: bump it, move CHANGELOG "Unreleased" items into a dated section, commit, `git tag -a vX.Y.Z -m "Balance Streamer X.Y.Z"`, push main then the tag, then `gh release create vX.Y.Z --verify-tag --notes-file <section>`.
- Commits use the GitHub noreply address set in this clone's git config; end AI-assisted commits with a `Co-Authored-By:` trailer.

## Code map (`balance_streamer/` package; `multi_balance_stream.py` is only the entry script)
- `app.py`: `main()` sets up logging first (`logs.py`, via the shared `crash_log.py`; `multi_balance_stream.py` calls it even earlier, before the heavy imports), chdirs into the data folder (`paths.enter_data_dir()`), takes the single-instance lock, sets the theme (`theme.py`, Qt Fusion + palettes), opens the window. If start-up fails after the window exists, `discard_windows()` deletes it (without closing, so nothing is saved) before the error goes on; left to Python's shutdown, the window could outlive the QApplication and segfault (exit 139). Importing the package has no side effects.
- Shared modules at the repo root, byte-identical in every UAkron app (never edit; ship them in `only-include`): `settings_location.py`, `crash_log.py` (log file, uncaught-error hooks), `single_instance.py` (one copy at a time: call `single_instance.release()` right before anything that starts a new copy; every restart, including `ReorderPanelsWidget.apply`, goes through `MultiBalanceApp.restart_app`, which does it) and `diagnostics.py` (Open Log Folder / Copy Diagnostics in `diagnostics_panel.py`).
- `serial_worker.py` `SerialWorker(QThread)`: reads one balance and emits Qt signals. Never touch widgets from this thread. `parsers.py` decodes lines for Bonvoisin, Mettler Toledo (MT-SICS), Ohaus Adventurer and Lachoi. Manuals are in `Ignore/Balance Brands/`.
- `balance_tab.py` `BalanceTab`: one tab per balance (layout, connection, recording, chart, table). Its methods are split into mixins: `flow.py` (flow maths), `export.py` (file names, Excel, PNG), `recovery.py` (backup CSV pruning and Recover Session), `tab_config.py` (saved tab settings).
- `settings_tab.py` (`SettingsTab`, `GlobalSavingSettingsWidget`), `widgets.py` (`CollapsibleBox`, `ReorderPanelsWidget`), `main_window.py` (`MultiBalanceApp`).
- Window size/position and each tab's splitters are per computer in `window_state.json` in the app folder (gitignored; `main_window.load_window_state`/`save_window_state`), not in config.json. Older versions' `app_geometry`/`splitter_state` keys in config.json are read only until this computer has its own, and left in place.
- `shortcut.py` + `shortcut_panel.py`: desktop icon. Windows: .lnk via PowerShell/WScript.Shell targeting the venv's pythonw.exe with `assets/Analytical Balance.ico`. Mac: `~/Desktop/Balance Streamer.app` whose `Contents/MacOS/launch` script execs this clone's Python (icon converted to .icns with Pillow). At startup `shortcut_panel.startup_check` offers the icon once per computer and refreshes it when the version changed; that state is in `local_state.json` in the app folder (gitignored, per computer — not config.json, which is shared through SyncThing).
- Launchers start without a terminal: `Launch_Windows.bat` (visible import check, then `start "" pythonw`) and `Launch_Mac.command` (import check, detached start, closes its Terminal window via `osascript`) both create `.venv` and install on first run, like `Setup_*` (now repair/reinstall only). `Balance Streamer.app` (committed, relative paths) runs `.venv/bin/python`. `Troubleshoot_Windows.bat` / `Troubleshoot_Mac.command` run the app with its output visible. `multi_balance_stream.py` catches start-up failures, logs them to the crash log and shows a native message box.
- Status bar (bottom right): `update_panel.VersionStatus` shows the version; the quiet startup check (`check_updates_on_start` in config, default on) turns it orange with an "Update to …" link. Background work uses `update_panel._Task` (daemon thread + queued signal), never QThread, so closing the window mid-check can't abort the app.
- `updater.py` + `update_panel.py`: Check for Updates. Fast-forwards a git clone to the latest release tag, reinstalls requirements, rolls back on failure, restarts.
- Errors: log with `logging.getLogger(__name__)`; they land in `logs/balance_streamer.log` in the data folder. Don't add bare `except:` or silent `except: pass` (ruff blocks them). Uncaught errors are logged and shown instead of closing the app.

## Behaviour to preserve
- Flow-rate derivative engines: Savitzky-Golay, Butterworth, EMA (scipy). These were carried over unchanged from the old tkinter version; don't change the math without being asked.
- Crash protection: session data is continuously written to `Data Backups/*.csv` and pruned after 30 days. "Recover Session" restores it.
- Exported files go to `Data/` and are named with the **true run start time**:
  `YYYY-MM-DD HHMMSS Flow rate C<1|2> <Material> 8cm <rate> mL_min R<##> <S|D>.xlsx`. The RTD dashboard in the parent folder depends on this format.
- `Data/`, `Data Backups/`, `config.json`, `*.csv`, `build/`, `dist/`, `*.spec` are gitignored. Keep it that way.

## History (Antigravity Jul–Oct 2026, Claude since 10 Oct 2026)
- Jul 2026: full rewrite from tkinter/customtkinter to PyQt6 (QThread serial workers, QtAgg matplotlib, native Qt dialogs). The old version was backed up as `multi_balance_stream_backup_ctk.py`.
- Jul–Sep 2026: added adaptive smoothing / Fornberg-derivative work and a pump-smoothing animation (`Data/Pump_N_Animation.mp4`).
- Sep 2026: older exports were renamed to their true start time to match the conductivity and pump logs.
- 2 Oct 2026: folders reorganized; logs and archive gitignored.
- 10 Oct 2026 onward: development with Claude (Anthropic).
- 14 Oct 2026: repo modernized (history rewritten to remove personal email and paths, pyproject, ruff, tests, CI) and released as v1.0.0.
- 14 Oct 2026: v1.1.0 split the script into the `balance_streamer` package, added Check for Updates, an error log, Qt's own theme instead of pyqtdarktheme, and fixed the Timestamp axis.
- 14 Oct 2026: v1.1.1 fixed the update check on python.org Python (certifi).
- 15 Oct 2026: v1.2.0 added Create Desktop Shortcut and the app/window icon.
- 15 Oct 2026: v1.3.0 added the version/out-of-date corner, the startup update check, launchers without a terminal, and the automatic desktop icon.

## Where code and data live
- **Code** (this repo) is cloned outside SyncThing: `%USERPROFILE%\GitHub Projects\UAkron\Balance-Streamer-GUI` on Windows, `~/GitHub Projects/UAkron/Balance-Streamer-GUI` on the Mac. It syncs through GitHub only.
- **Instrument data** stays in SyncThing: `%USERPROFILE%\SyncThing\UAkron Playground\Balance Streamer Application\` (Mac: `~/SyncThing/UAkron Playground/Balance Streamer Application/`). Never copy data into the repo, and never commit the settings files listed below.
- **How it works:** at startup the app `chdir`s into its SyncThing data folder (`DATA_DIR`, override with `UAKRON_APP_DATA_DIR` or `UAKRON_DATA_DIR`). Every relative data path (`Data/`, `Data Backups/`, `Sessions/`, run logs) therefore resolves inside SyncThing, and the default save folder is `Data` there. Files that ship with the code (icons, the OCR model) must be loaded via `paths.REPO_DIR` / `__file__`, never by bare relative name. Run the app from this clone.
- **Settings folder (since 10 Oct 2026):** the settings files (`config.json`) are read from `CONFIG_DIR`, resolved by `settings_location.py` (identical copy in every UAkron repo). Default: this repo folder (gitignored), so a fresh clone starts from the app's defaults. The per-machine pointer `settings_location.json` (gitignored), set from the app's "Settings Folder" box, can move them; a relative path is relative to the data folder. Brandon's machines point at `Settings`, i.e. `UAkron Playground/<App>/Settings/` in SyncThing, so settings stay identical across computers (including `secrets.json`; never print it). `UAKRON_SETTINGS_DIR` overrides the pointer. Store save folders relative to the data folder (e.g. `Data`), not as absolute paths.

## Launch
Double-click `Launch_Windows.bat` (Windows) / `Launch_Mac.command` or `Balance Streamer.app` (Mac), or the desktop icon. They use this repo's `.venv`; the `Launch_*` files create it on first run (or: `python -m venv .venv` and `pip install -r requirements.txt`). Windows Smart App Control is on for the lab PC; if a DLL import is "blocked by an Application Control policy", retry once before investigating.
