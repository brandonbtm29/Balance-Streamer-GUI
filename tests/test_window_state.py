"""The window's size, position and dividers are kept per computer, not in the synced config.json."""

import contextlib
import json
import os

import pytest
from PyQt6.QtCore import QSize
from PyQt6.QtWidgets import QApplication

from balance_streamer import main_window
from balance_streamer.main_window import MultiBalanceApp
from balance_streamer.paths import REPO_DIR


@contextlib.contextmanager
def _another_window():
    """A second window, as when the app starts again; closed (and so saved) afterwards."""
    win = MultiBalanceApp()
    try:
        yield win
    finally:
        for tab in win.tab_objects:
            tab.update_timer.stop()
        win.close()
        win.deleteLater()
        import matplotlib.pyplot as plt  # here: the app picks matplotlib's Qt backend first

        plt.close("all")


def _local_state():
    with open(main_window.WINDOW_STATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _saved_config(window):
    with open(window.config_path, encoding="utf-8") as f:
        return json.load(f)


def _show_normal(window, size):
    """A normal (not maximized) window of about this size; the offscreen test screen is 800x800."""
    window.showNormal()
    window.resize(size)
    QApplication.processEvents()
    return window.size()  # may be larger than asked: the window has a minimum size


def test_layout_is_saved_on_this_computer_not_in_config(window):
    window.config.pop("app_geometry", None)
    tab = window.tab_objects[0]
    size = _show_normal(window, QSize(700, 650))
    tab.splitter.setSizes([300, 700, 300])
    QApplication.processEvents()
    splitter_sizes = tab.splitter.sizes()
    window.close()  # saved on close

    state = _local_state()
    assert state["geometry"] and set(state["tabs"][tab.tab_name]) == {"splitter_state", "mid_splitter_state"}
    config = _saved_config(window)
    assert "app_geometry" not in config
    assert "splitter_state" not in config["known_balances"][tab.tab_name]["settings"]

    with _another_window() as again:  # restored next time
        again.show()
        QApplication.processEvents()
        assert again.size() == size
        same_tab = next(t for t in again.tab_objects if t.tab_name == tab.tab_name)
        assert same_tab.splitter.sizes() == splitter_sizes


def test_layout_from_an_older_version_is_used_until_this_computer_has_its_own(window):
    old_size = _show_normal(window, QSize(700, 650))
    old_geometry = window.saveGeometry().toHex().data().decode()
    window.config["app_geometry"] = old_geometry  # where older versions kept it (config.json)
    window.save_config()
    try:
        assert not os.path.exists(main_window.WINDOW_STATE_PATH)
        with _another_window() as again:
            again.show()
            QApplication.processEvents()
            assert again.size() == old_size  # used once
            new_size = _show_normal(again, old_size + QSize(60, 40))
        assert _local_state()["geometry"]  # from now on this computer has its own
        assert _saved_config(window)["app_geometry"] == old_geometry  # left as it was, for older versions
        with _another_window() as third:
            third.show()
            QApplication.processEvents()
            assert third.size() == new_size
    finally:
        window.config.pop("app_geometry", None)  # don't leave it for the other tests


def test_dividers_from_an_older_version_are_used_and_kept_in_config(window):
    tab = window.tab_objects[0]
    old_state = tab.layout_state()
    balance = window.config["known_balances"].setdefault(tab.tab_name, {"brand": "", "port": ""})
    balance.setdefault("settings", {})["splitter_state"] = old_state["splitter_state"]
    restored = []
    tab.restore_layout = restored.append
    try:
        tab.load_tab_settings()  # no window_state.json yet: the old value from config.json is used
        assert restored[-1]["splitter_state"] == old_state["splitter_state"]
        tab.save_tab_settings()
        settings = window.config["known_balances"][tab.tab_name]["settings"]
        assert settings["splitter_state"] == old_state["splitter_state"]  # left for older versions
        assert "mid_splitter_state" not in settings  # nothing new is written there
    finally:
        window.config["known_balances"][tab.tab_name]["settings"].pop("splitter_state", None)


def test_first_start_keeps_the_default_size(qapp, monkeypatch):
    monkeypatch.setattr(MultiBalanceApp, "restoreGeometry", lambda *a: pytest.fail("nothing to restore"))
    with _another_window() as win:
        assert win.size() == QSize(1400, 800)  # and main() then shows it maximized, as before


def test_window_off_screen_last_time_comes_back_on_screen(window):
    _show_normal(window, QSize(700, 650))
    window.move(6000, 5000)  # e.g. on a second monitor that is now unplugged
    QApplication.processEvents()
    window.remember_window_state()
    with _another_window() as again:
        again.show()
        QApplication.processEvents()
        assert again.geometry().intersects(QApplication.primaryScreen().availableGeometry())


def test_unreadable_window_state_is_ignored(qapp):
    with open(main_window.WINDOW_STATE_PATH, "w", encoding="utf-8") as f:
        f.write("{not json")
    with _another_window() as win:
        assert win.tab_objects
    with open(main_window.WINDOW_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"geometry": 5, "tabs": {"Balance 1": "x"}}, f)
    with _another_window() as win:
        assert win.tab_layout("Balance 1") == {}


def test_window_state_file_is_gitignored():
    with open(os.path.join(REPO_DIR, ".gitignore"), encoding="utf-8") as f:
        assert main_window.WINDOW_STATE_FILE in f.read().split()


def test_replace_file_retries_when_windows_denies_access(tmp_path, monkeypatch):
    """SyncThing or antivirus holding config.json for a moment must not lose the settings."""
    src, dst = tmp_path / "config.json.tmp", tmp_path / "config.json"
    src.write_text("new")
    dst.write_text("old")
    real_replace, calls = os.replace, []

    def flaky(a, b):
        calls.append(1)
        if len(calls) < 3:
            raise PermissionError(13, "Access is denied")
        real_replace(a, b)

    monkeypatch.setattr(main_window.os, "replace", flaky)
    monkeypatch.setattr(main_window.time, "sleep", lambda s: None)
    main_window.replace_file(str(src), str(dst))
    assert dst.read_text() == "new" and len(calls) == 3


def test_replace_file_gives_up_after_a_while(tmp_path, monkeypatch):
    def always_denied(a, b):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(main_window.os, "replace", always_denied)
    monkeypatch.setattr(main_window.time, "sleep", lambda s: None)
    with pytest.raises(PermissionError):
        main_window.replace_file("a", "b", attempts=3)
