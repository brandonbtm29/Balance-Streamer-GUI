# Changelog

All notable changes to Balance Streamer. Versions follow [Semantic Versioning](https://semver.org/):
new features bump the middle number (1.0.0 → 1.1.0) and fixes bump the last (1.0.0 → 1.0.1).

## [Unreleased]

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

[Unreleased]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/brandonbtm29/Balance-Streamer-GUI/releases/tag/v1.0.0
