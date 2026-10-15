# Security policy

## Reporting a vulnerability

Please **don't** open a public issue for security problems. Use GitHub's
"Report a vulnerability" button (Security tab → Advisories) to report privately.
I'll reply within a week.

## Security model

Balance Streamer is a desktop app with no network features. It talks only to balances on the
computer's serial ports and writes files to its own data and settings folders. It stores no
passwords or keys.

Things that would count as security issues:

- The app reading or writing files outside its data folder, settings folder, or a folder you chose
- A crafted reading from a serial device causing code to run or files to be overwritten
- Personal data or secrets ending up in the repository or its history
