"""Problems are logged and handled instead of silently ignored."""

import logging
import os

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


def test_log_file_is_written(tmp_path, monkeypatch):
    from balance_streamer import logs

    monkeypatch.chdir(tmp_path)
    root = logging.getLogger()
    before = list(root.handlers)
    try:
        logs.setup_logging()
        logging.getLogger("balance_streamer.test").warning("hello from the test")
        for h in root.handlers:
            h.flush()
        text = (tmp_path / "logs" / "balance_streamer.log").read_text(encoding="utf-8")
        assert "hello from the test" in text
    finally:
        for h in list(root.handlers):
            if h not in before:
                root.removeHandler(h)
                h.close()
