"""Settings → Application Settings → Troubleshooting: Open Log Folder and Copy Diagnostics."""

import pytest

import balance_streamer
import crash_log
import diagnostics
from balance_streamer import diagnostics_panel


@pytest.fixture
def panel(window):
    return window.settings_tab.diagnostics_panel


@pytest.fixture
def log_file(tmp_path):
    crash_log._reset_for_tests()
    path = crash_log.setup("balance_streamer", str(tmp_path / "logs"), qt_dialog=False)
    yield path
    crash_log._reset_for_tests()


def test_buttons_are_in_application_settings(window, panel):
    assert panel.btn_open_logs.text() == "Open Log Folder"
    assert panel.btn_copy.text() == "Copy Diagnostics"
    assert window.settings_tab.isAncestorOf(panel)


def test_copy_diagnostics_puts_a_report_on_the_clipboard(qapp, panel, log_file):
    qapp.clipboard().clear()
    panel.btn_copy.click()
    text = qapp.clipboard().text()
    assert text.startswith(f"Balance Streamer {balance_streamer.__version__}")
    assert "Log file:" in text and "balance_streamer.log" in text
    assert "Balances configured: 1" in text and "Balance 1: " in text
    assert panel.lbl_status.text().startswith("Diagnostics copied.")


class _Box:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text


class _Reader:
    def isRunning(self):
        return True


class _Tab:
    def __init__(self, brand, port, reader=None, recording=False):
        self.tab_name = "Column 7 run"
        self.combo_brand, self.combo_com = _Box(brand), _Box(port)
        self.serial_thread, self.recording = reader, recording


def test_balance_summary_lists_brands_and_ports_not_tab_names():
    lines = diagnostics_panel.balance_summary(
        [_Tab("Mettler Toledo", "COM7", _Reader(), recording=True), _Tab("Bonvoisin", "No Ports Found")]
    )
    assert lines == {
        "Balances configured": "2",
        "Balance 1": "Mettler Toledo on COM7 (connected, recording)",
        "Balance 2": "Bonvoisin on no port chosen (not connected)",
    }


def test_open_log_folder_opens_the_logs_folder(panel, log_file, monkeypatch):
    opened = []
    monkeypatch.setattr(diagnostics, "open_folder", opened.append)
    panel.btn_open_logs.click()
    assert opened == [diagnostics.log_folder(log_file)]


def test_open_log_folder_explains_a_problem(panel, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    def fail(_folder):
        raise OSError("There is no folder to open yet.")

    warned = []
    monkeypatch.setattr(diagnostics, "open_folder", fail)
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warned.append(a[2]))
    panel.btn_open_logs.click()
    assert warned and "There is no folder to open yet." in warned[0]
