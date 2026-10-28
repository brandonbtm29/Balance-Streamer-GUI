"""Problems are logged and handled instead of silently ignored."""

import logging
import os
import sys

from balance_streamer.paths import CONFIG_DIR


def test_unreadable_settings_are_kept_aside(qapp, caplog):
    from balance_streamer.main_window import MultiBalanceApp

    config = os.path.join(CONFIG_DIR, "config.json")
    with open(config, "w", encoding="utf-8") as f:
        f.write("{ this is not json")
    try:
        with caplog.at_level(logging.ERROR):
            win = MultiBalanceApp()
        assert "starting from default settings" in caplog.text
        with open(config + ".unreadable", encoding="utf-8") as f:
            assert f.read() == "{ this is not json"  # the user's file survives
        for tab in win.tab_objects:
            tab.update_timer.stop()
        win.close()
    finally:
        for path in (config, config + ".unreadable"):
            if os.path.exists(path):
                os.remove(path)


def test_backup_scan_skips_damaged_rows(tab):
    with open(tab.backup_path, "w", encoding="utf-8", newline="") as f:
        f.write("Timestamp,Duration (min),Mass (g),Flow Rate (g/min)\n")
        f.write("2026-01-15 10:00:00.000,0.0,1.0,\n")
        f.write("2026-01-15 10:00:01.000,not a number,1.1,\n")
        f.write("2026-01-15 10:00:02.000,0.03333,1.2,\n")
    sessions = tab.scan_backup_sessions()
    assert len(sessions) == 1
    assert sessions[0]["points"] == 2


def test_log_file_is_written(data_dir):
    import crash_log
    from balance_streamer import logs

    crash_log._reset_for_tests()
    try:
        path = logs.setup_logging()
        assert path == os.path.join(str(data_dir), "logs", "balance_streamer.log")
        assert logs.setup_logging() == path  # safe to call twice
        assert sys.excepthook.__module__ == "crash_log"  # the only hook: crash_log's
        logging.getLogger("balance_streamer.test").warning("hello from the test")
        for h in logging.getLogger().handlers:
            h.flush()
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert "balance_streamer" in text and "starting" in text
        assert "hello from the test" in text
    finally:
        crash_log._reset_for_tests()


def test_log_falls_back_to_the_user_folder(tmp_path, monkeypatch):
    """A data folder that can't be written to (e.g. read-only SyncThing) still leaves a log."""
    import crash_log
    from balance_streamer import logs

    blocker = tmp_path / "not_a_folder"
    blocker.write_text("x")
    monkeypatch.setattr(logs, "LOG_DIR", str(blocker / "logs"))
    monkeypatch.setattr(crash_log, "user_log_dir", lambda name: str(tmp_path / "user" / name / "logs"))
    crash_log._reset_for_tests()
    try:
        path = logs.setup_logging()
        assert path == str(tmp_path / "user" / "Balance Streamer" / "logs" / "balance_streamer.log")
    finally:
        crash_log._reset_for_tests()
