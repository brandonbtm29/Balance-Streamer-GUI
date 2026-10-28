# Changelog

All notable changes to Balance Streamer. Versions follow [Semantic Versioning](https://semver.org/):
new features bump the middle number (1.0.0 → 1.1.0) and fixes bump the last (1.0.0 → 1.0.1).

## [Unreleased]

## [1.4.0] - 2026-10-28

### Added
- `Setup_Windows.bat` / `Setup_Mac.command`: one double-click creates the `.venv` and installs everything.
  Since the launchers now do this by themselves (below), these are for repairing or reinstalling.
- **The launchers set the app up the first time.** Double-click `Launch_Windows.bat` or
  `Launch_Mac.command` on a new computer: it creates the `.venv` folder and installs what the app
  needs (this takes a minute or two), then starts the app. One file to double-click, first time and
  every time. If something goes wrong it shows why and waits for you instead of closing.
- **Only one copy at a time.** Opening Balance Streamer while it is already running brings the open
  window to the front, instead of starting a second copy that would fight over the same balances.
  Restart and Update and Restart still work as before.
- **Open Log Folder** and **Copy Diagnostics** in Settings → Application Settings → Troubleshooting.
  Copy Diagnostics copies the app version, your system, where the app keeps its files, how many
  balances are set up with their brands and ports, and the end of the log, ready to paste into a
  GitHub issue or an email. Your home folder is shortened to `~` and anything that looks like a
  password is blanked.
- `Troubleshoot_Windows.bat` and `Troubleshoot_Mac.command` run the app with its messages shown in a
  console window, for when something goes wrong.
- Dependabot keeps the GitHub Actions and Python dependencies up to date.

### Changed
- `Launch_Mac.command` now starts the app without keeping Terminal open: its window closes once the
  app has started. Showing the app's messages in Terminal moved to `Troubleshoot_Mac.command`.
- `Launch_Windows.bat` first checks that the app's packages work. If they don't, it says why in a
  window that stays open, instead of nothing happening.
- **Where the logs go:** still `logs/balance_streamer.log` in the data folder, which now also gets
  errors at start-up. They used to go to `startup-error.log` in the app's folder; that file is no
  longer written and can be deleted. A hard crash (in a driver or in Qt) is written to
  `logs/balance_streamer.fatal.log`. If the data folder can't be written to, the logs go to
  `%LOCALAPPDATA%\Balance Streamer\logs` on Windows or `~/Library/Logs/Balance Streamer` on a Mac.
- **Each computer remembers its own window size and position**, and the dividers in each balance
  tab. They used to be saved in `config.json`, so with a shared settings folder a Mac's layout was
  applied on the Windows PC. They are now in `window_state.json` in the app's folder. The first
  time, the app opens with the size and position the older version saved.

### Fixed
- **Apply and Restart** (Settings → Panel Management) now restarts the way Update and Restart does:
  it saves your tabs and disconnects the balances first, so the restarted app can open their ports.
  If a recording is running, it asks before restarting.
- If the app couldn't finish starting, it sometimes crashed while closing, after its message saying
  why, and left a confusing entry in `logs/balance_streamer.fatal.log`. It now closes normally.
- `Balance Streamer.app` in the app's folder: its "isn't set up yet" message now says to
  double-click `Launch_Mac.command`, which sets the app up.
- On Windows, saving settings sometimes failed with "Access is denied" when SyncThing or antivirus
  had `config.json` open for a moment, so the change was lost. The app now retries for about a second.

## [1.3.0] - 2026-10-15

### Added
- **Version in the bottom-right corner** of the window. When a newer release is out it turns orange
  and says the version is **out of date**, with an **Update to …** link that opens the update.
- **Update check at startup**: the app asks GitHub for the latest release a moment after it opens.
  Turn it off with **Check for updates when the app starts** in Settings → Application Settings.
- **Desktop icon without asking twice**: the first time the app starts on a computer it offers to
  put a Balance Streamer icon (with the balance picture) on the desktop, and after each update it
  refreshes that icon by itself.
- **Balance Streamer.app** in the app's folder on macOS: double-click it to start the app without
  a Terminal window.
- If the app can't start, it says why in a message box and writes `startup-error.log`.

### Changed
- `Launch_Windows.bat` starts the app without leaving a console window open.
- `Launch_Mac.command` is now the troubleshooting launcher (it shows the app's messages in Terminal).
- On Windows the app has its own taskbar entry and icon instead of grouping with other Python programs.
- The Mac desktop icon is made with Pillow, so it no longer depends on macOS's `sips` tool.

### Fixed
- Closing a balance tab within half a second of opening it could raise an error when its delayed
  auto-connect fired.

## [1.2.0] - 2026-10-15

### Added
- **Create Desktop Shortcut** (Settings → Application Settings). On Windows it makes a desktop
  shortcut with the balance icon that opens the app without the black console window. On a Mac it
  makes a small Balance Streamer app on the desktop that you can also drag to the Dock or
  Applications. The shortcut starts this copy of the app, so it keeps working after updates, and
  pressing the button again replaces it.
- The app's windows, taskbar entry and Dock icon now show the balance icon.

## [1.1.1] - 2026-10-14

### Fixed
- **Check for Updates** said "Couldn't reach GitHub" on Macs that use Python from python.org,
  which has no certificate store of its own. It now brings its own certificates (the `certifi`
  package), and a certificate problem gets its own message.
- An update check that fails for an expected reason (offline, no releases yet) no longer writes a
  full error trace to the log.

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

[Unreleased]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.4.0...HEAD
[1.4.0]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.1.1...v1.2.0
[1.1.1]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.1.0...v1.1.1
[1.1.0]: https://github.com/brandonbtm29/Balance-Streamer-GUI/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/brandonbtm29/Balance-Streamer-GUI/releases/tag/v1.0.0
