"""Shared test setup.

Importing the app moves the working directory into its data folder and reads its
settings folder, so both are pointed at a throwaway folder before anything is
imported (and deleted when the tests finish). Qt runs headless, so the tests work
without a screen (CI, SSH).
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

_START_DIR = os.getcwd()
_TMP = Path(tempfile.mkdtemp(prefix="balance-streamer-tests-"))
os.environ["UAKRON_APP_DATA_DIR"] = str(_TMP / "data")
os.environ["UAKRON_SETTINGS_DIR"] = str(_TMP / "settings")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def pytest_sessionfinish(session, exitstatus):
    """Delete the throwaway folder. The tests run inside it, so step out first (Windows needs that)."""
    os.chdir(_START_DIR)
    shutil.rmtree(_TMP, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def data_dir():
    """Run every test inside the throwaway data folder, as the app does with the real one."""
    from balance_streamer.paths import DATA_DIR, enter_data_dir

    enter_data_dir()
    return Path(DATA_DIR)


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp):
    """A fresh main window with its default balance tab."""
    from balance_streamer.main_window import MultiBalanceApp

    win = MultiBalanceApp()
    yield win
    for tab in list(win.tab_objects):
        tab.update_timer.stop()
    win.close()
    win.deleteLater()
    import matplotlib.pyplot as plt

    plt.close("all")  # each balance tab opens a pyplot figure; don't keep them for the whole session


@pytest.fixture
def tab(window):
    return window.tab_objects[0]


@pytest.fixture(autouse=True)
def _private_shortcut_state(tmp_path, monkeypatch):
    """Keep the per-computer shortcut state and window layout files out of the real app folder."""
    from balance_streamer import main_window, shortcut

    monkeypatch.setattr(shortcut, "STATE_FILE", str(tmp_path / "local_state.json"))
    monkeypatch.setattr(main_window, "WINDOW_STATE_PATH", str(tmp_path / "window_state.json"))
