"""Shared test setup.

Importing the app moves the working directory into its data folder and reads its
settings folder, so both are pointed at a throwaway folder before anything is
imported. Qt runs headless, so the tests work without a screen (CI, SSH).
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest

_TMP = Path(tempfile.mkdtemp(prefix="balance-streamer-tests-"))
os.environ["UAKRON_APP_DATA_DIR"] = str(_TMP / "data")
os.environ["UAKRON_SETTINGS_DIR"] = str(_TMP / "settings")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


@pytest.fixture(scope="session")
def mbs():
    """The app module, imported with the test folders in place."""
    import multi_balance_stream

    return multi_balance_stream


@pytest.fixture(scope="session")
def qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qapp, mbs):
    """A fresh main window with its default balance tab."""
    win = mbs.MultiBalanceApp()
    yield win
    for tab in list(win.tab_objects):
        tab.update_timer.stop()
    win.close()
    win.deleteLater()


@pytest.fixture
def tab(window):
    return window.tab_objects[0]
