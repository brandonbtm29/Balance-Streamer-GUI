# Security policy

## Reporting a vulnerability

Please **don't** open a public issue for security problems. Use GitHub's
"Report a vulnerability" button (Security tab → Advisories) to report privately.
I'll reply within a week.

## Security model

Balance Streamer is a desktop app. It talks to balances on the computer's serial ports and writes
files to its own data and settings folders. It stores no passwords or keys.

It goes online only to check for updates, when it starts (this can be turned off in Settings) and
when you press **Check for Updates**: it asks GitHub's public API for this repository's latest
release (no account, nothing about you is sent), and if you choose to update,
it runs `git fetch` from the folder's own `origin` remote, checks that the release tag's commit is
signed with a key in `.github/allowed_signers` (this computer's own copy, so a release can't add its
own key), moves to the tag (fast-forward only) and runs `pip install -r requirements.txt` with the
app's Python. git and pip run without any `GIT_*` settings from the environment.

Things that would count as security issues:

- The app reading or writing files outside its data folder, settings folder, or a folder you chose
- A crafted reading from a serial device causing code to run or files to be overwritten
- The updater installing anything other than a published release of this repository
- Personal data or secrets ending up in the repository or its history
