# Changelog

All notable changes to Balance Streamer. Versions follow [Semantic Versioning](https://semver.org/):
new features bump the middle number (1.0.0 → 1.1.0) and fixes bump the last (1.0.0 → 1.0.1).

## [Unreleased]

## [1.1.0] - 2026-10-14

### Added
- **Check for Updates** (Settings → Application Settings) replaces Restart Application. It shows the
  running version, asks GitHub for the latest release, and can update a `git clone` copy to it and
  restart. It never pulls unreleased work, never overwrites files you changed, and goes back to the
  old version if installing the new requirements fails. ZIP copies and standalone builds get a link
  to the release page.
- **Error log** at `logs/balance_streamer.log` in the data folder. Problems that used to be skipped
  silently are now recorded there.
- `python -m balance_streamer` starts the app.

### Changed
- An error nobody expected is now logged and shown in a message instead of closing the app, so a
  recording keeps going.
- If the backup file can't be written, the tab's status says so (recording carries on).
- An unreadable `config.json` is kept as `config.json.unreadable` instead of being overwritten with
  the default settings.
- The dark and light themes now use Qt's built-in Fusion style with the same colours, replacing the
  `pyqtdarktheme` package. Ticked check boxes are easier to see in dark mode.
- The Help page lists the four supported balances and their serial settings correctly. It no longer
  tells Mettler Toledo and Ohaus users to turn on continuous mode, which the app doesn't need.
- The code is now the `balance_streamer` package instead of one 2,600-line script.
  `multi_balance_stream.py` still starts the app, so the launchers work as before.

### Fixed
- The chart's **Timestamp** axis showed Duration instead of clock time, so gaps after a pause or a
  recovered session never appeared.
- Recover Session could leave the time and mass columns different lengths when a backup row was
  damaged; damaged rows are now skipped whole.
- Logging a calibration point or restoring a session no longer fails without a message.

### Upgrading from 1.0.0
1.0.0 has no update button. Update once by hand in the app's folder:
`git pull`, then `pip install -r requirements.txt` with the virtual environment's Python
(`.venv\Scripts\python -m pip install -r requirements.txt` on Windows,
`.venv/bin/python -m pip install -r requirements.txt` on macOS). After that, use Check for Updates.

## [1.0.0] - 2026-10-14

First tracked release. The app has been in daily lab use since mid-2026; this release gives it a
version number, tests and a proper README.

### What it does
- Streams several balances at once (Mettler Toledo, Ohaus Adventurer, Bonvoisin, Lachoi), one tab each.
- Live mass and flow-rate chart with Savitzky-Golay derivatives and Mean, Median, EMA, Butterworth or
  Adaptive smoothing.
- Excel export with a documentation sheet, data and chart; file names from token templates.
- Auto-save, auto-stop, Quick Save, crash-recovery backups (kept 30 days) and Recover Session.
- Data and settings live outside the code folder and can be shared between computers through a
  synced folder.

### Added
- `balance-streamer` command when installed with pip.
- Automated tests (balance parsers, flow rates, file names, Excel export) that run without a screen.
- Continuous integration on Windows, macOS and Linux, with a secret scan of the whole history.
- README with a screenshot, setup steps for Windows and macOS, and an explanation of where files go.

### Changed
- Dependencies are listed in `pyproject.toml` with minimum versions; `requirements.txt` still works
  for the launchers and `build_app.py`.
- The theme library `pyqtdarktheme` is pinned to 0.1.7 so every computer gets the same look.

Earlier versions were co-developed with Google Gemini in Antigravity; development continues with
Claude (Anthropic).

[Unreleased]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/brandonbtm29/Balance-Streamer-GUI/releases/tag/v1.0.0
