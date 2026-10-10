# Balance Streamer Application

PyQt6 desktop app that streams several lab balances at once over RS-232/USB serial, computes live flow rates from mass, and exports `.xlsx` with embedded charts. Part of Brandon's UAkron lab workspace (shared conventions in `../CLAUDE.md` when the repos are cloned side by side in `GitHub Projects/UAkron/`). GitHub: `brandonbtm29/Balance-Streamer-GUI`.

## Run / build / test
- Install: `pip install -r requirements.txt` (PyQt6, pyqtdarktheme, pyserial, matplotlib, openpyxl, scipy, pyinstaller)
- Run: `python multi_balance_stream.py`
- Build executable: `python build_app.py` → `dist/Balance_Streamer/` (PyInstaller `--onedir`, excludes PyQt5/PySide6)
- Tests: `python -m pytest tests`

## Code map (`multi_balance_stream.py`, ~2,300 lines)
- `SerialWorker(QThread)`: reads one balance and emits Qt signals. Never touch widgets from this thread.
- `BalanceTab`: one tab per balance (plot, filters, export).
- `SettingsTab`, `GlobalSavingSettingsWidget`, `ReorderPanelsWidget`: app-wide settings.
- `MultiBalanceApp(QMainWindow)`: main window.
- Parsers support Bonvoisin, Mettler Toledo (MT-SICS), Ohaus Adventurer and Lachoi balances. Manuals are in `Ignore/Balance Brands/`.

## Behaviour to preserve
- Flow-rate derivative engines: Savitzky-Golay, Butterworth, EMA (scipy). These were carried over unchanged from the old tkinter version; don't change the math without being asked.
- Crash protection: session data is continuously written to `Data Backups/*.csv` and pruned after 30 days. "Recover Session" restores it.
- Exported files go to `Data/` and are named with the **true run start time**:
  `YYYY-MM-DD HHMMSS Flow rate C<1|2> <Material> 8cm <rate> mL_min R<##> <S|D>.xlsx`. The RTD dashboard in the parent folder depends on this format.
- `Data/`, `Data Backups/`, `config.json`, `*.csv`, `build/`, `dist/`, `*.spec` are gitignored. Keep it that way.

## History (from Antigravity, Jul–Oct 2026)
- Jul 2026: full rewrite from tkinter/customtkinter to PyQt6 (QThread serial workers, QtAgg matplotlib, native Qt dialogs). The old version was backed up as `multi_balance_stream_backup_ctk.py`.
- Jul–Sep 2026: added adaptive smoothing / Fornberg-derivative work and a pump-smoothing animation (`Data/Pump_N_Animation.mp4`).
- Sep 2026: older exports were renamed to their true start time to match the conductivity and pump logs.
- 2 Oct 2026: folders reorganized; logs and archive gitignored.

## Where code and data live
- **Code** (this repo) is cloned outside SyncThing: `C:\Users\Brand\GitHub Projects\UAkron\Balance-Streamer-GUI` on Windows, `~/GitHub Projects/UAkron/Balance-Streamer-GUI` on the Mac. It syncs through GitHub only.
- **Instrument data** stays in SyncThing: `C:\Users\Brand\SyncThing\UAkron Playground\Balance Streamer Application\` (Mac: `/Users/brandonmcreynolds/SyncThing/UAkron Playground/Balance Streamer Application/`). Never copy data, `config.json` or `secrets.json` into the repo.
- **How it works (since 10 Oct 2026):** at startup the app `chdir`s into its SyncThing data folder (`DATA_DIR`, override with `UAKRON_APP_DATA_DIR` or `UAKRON_DATA_DIR`). Every relative path (`Data/`, `Data Backups/`, `Sessions/`, run logs, local config such as `config.json` / `pump_config.json` / `jebao_config.json` / `secrets.json` / `global_rois.json`) therefore resolves inside SyncThing. Files that ship with the code (icons, the OCR model) must be loaded via `script_dir` / `__file__`, never by bare relative name. Run the app from this clone.

## Launch
Double-click `Launch_Windows.bat` / `Launch_Mac.command`. They use this repo's `.venv` (create it with `python -m venv .venv` and `pip install -r requirements.txt`). Windows Smart App Control is on for BTM-NOVA; if a DLL import is "blocked by an Application Control policy", retry once before investigating.
