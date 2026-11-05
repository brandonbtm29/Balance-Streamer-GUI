"""Ports per computer, time stamps, config saves, "close anyway?" prompts, the serial reader, logs."""

import contextlib
import json
import os
import time
from types import SimpleNamespace

import pytest
import serial
import serial.tools.list_ports
from PyQt6.QtCore import QEventLoop, QTimer
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMessageBox

from balance_streamer import main_window, serial_worker
from balance_streamer.main_window import MultiBalanceApp, pick_port
from balance_streamer.paths import CONFIG_DIR, REPO_DIR, computer_folder_name


def _ports(monkeypatch, *names):
    monkeypatch.setattr(
        serial.tools.list_ports, "comports", lambda *a, **k: [SimpleNamespace(device=n) for n in names]
    )


@contextlib.contextmanager
def _window_with(config=None, window_state=None):
    """A window started from this config.json (and this computer's window_state.json)."""
    config_path = os.path.join(CONFIG_DIR, "config.json")
    if config is not None:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f)
    if window_state is not None:
        with open(main_window.WINDOW_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(window_state, f)
    win = MultiBalanceApp()
    try:
        yield win
    finally:
        for tab in win.tab_objects:
            tab.update_timer.stop()
        win.close()
        win.deleteLater()
        if os.path.exists(config_path):
            os.remove(config_path)


def _no_serial(monkeypatch):
    """Record which ports the app tries to open, without opening any."""
    opened = []

    class FakeWorker:
        def __init__(self, port, baud, brand):
            opened.append(port)
            self.error_msg = "not a real port"
            self.port = port

        def isRunning(self):
            return False

        def stop(self):
            pass

        def wait(self, *args):
            return True

    monkeypatch.setattr("balance_streamer.balance_tab.SerialWorker", FakeWorker)
    return opened


def _process_events(ms=700):
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


# --- which port --------------------------------------------------------------------------------


def test_pick_port():
    assert pick_port("COM3", "COM12", ["COM3", "COM12"]) == "COM3"  # this computer's own first
    assert pick_port(None, "COM12", ["COM12"]) == "COM12"
    assert pick_port("/dev/cu.usbserial-1", "COM12", ["/dev/cu.debug-console"]) is None  # never a stand-in
    assert pick_port(None, "", ["COM1"]) is None


def test_saved_port_missing_here_is_not_swapped_for_another(qapp, monkeypatch):
    _ports(monkeypatch, "/dev/cu.debug-console", "/dev/cu.Bluetooth-Incoming-Port")
    opened = _no_serial(monkeypatch)
    config = {"known_balances": {"C1 Bonvoisin": {"brand": "Bonvoisin", "port": "COM12"}}}
    with _window_with(config) as win:
        tab = win.tab_objects[0]
        _process_events()  # the delayed auto-connect would have run by now
        assert opened == []
        assert tab.combo_com.currentIndex() == -1
        assert "COM12" in tab.lbl_status.text()
        assert win.config["known_balances"]["C1 Bonvoisin"]["port"] == "COM12"  # shared setting untouched


def test_port_used_on_this_computer_wins(qapp, monkeypatch):
    _ports(monkeypatch, "COM12", "/dev/ttyUSB0")
    opened = _no_serial(monkeypatch)
    config = {"known_balances": {"C1": {"brand": "Bonvoisin", "port": "COM12"}}}
    with _window_with(config, {"ports": {"C1": "/dev/ttyUSB0"}}) as win:
        assert win.tab_objects[0].combo_com.currentText() == "/dev/ttyUSB0"
        _process_events()
        assert opened == ["/dev/ttyUSB0"]


def test_connecting_remembers_the_port_and_keeps_tab_settings(window):
    window.config["known_balances"]["C1"] = {"brand": "Lachoi", "port": "COM9", "settings": {"interval": "3"}}
    window.save_connection("C1", "Lachoi", "/dev/ttyUSB1")
    entry = window.config["known_balances"]["C1"]
    assert entry["settings"] == {"interval": "3"}  # used to be dropped here
    assert entry["port"] == "/dev/ttyUSB1"
    assert window.port_here("C1") == "/dev/ttyUSB1"
    with open(main_window.WINDOW_STATE_PATH, encoding="utf-8") as f:
        assert json.load(f)["ports"]["C1"] == "/dev/ttyUSB1"


def test_two_tabs_cannot_share_a_port(window, monkeypatch):
    _ports(monkeypatch, "COM12")
    opened = _no_serial(monkeypatch)
    first = window.tab_objects[0]
    window.add_tab("Second")
    second = window.tab_objects[1]
    first.serial_thread = SimpleNamespace(port="COM12", isRunning=lambda: True, stop=lambda: None)
    second.refresh_com_ports()
    second.combo_com.setCurrentText("COM12")
    second.connect_serial(auto=True)
    assert opened == []
    assert "already in use" in second.lbl_status.text()
    first.serial_thread = None


def test_refresh_keeps_the_chosen_port(tab, monkeypatch):
    _ports(monkeypatch, "COM1", "COM5")
    tab.refresh_com_ports()
    tab.combo_com.setCurrentText("COM5")
    tab.refresh_com_ports()
    assert tab.combo_com.currentText() == "COM5"


# --- time stamps -------------------------------------------------------------------------------


def test_readings_are_timed_when_they_arrive_not_when_the_window_gets_to_them(tab):
    tab.ent_interval.setText("1")
    tab.toggle_record()
    start = tab.start_time
    tab.on_data_received(10.0, "g", start + 2.0)
    tab.on_data_received(10.1, "g", start + 3.0)  # handled late, but read 1 s after the first
    assert tab.times_sec == pytest.approx([2.0, 3.0])
    assert (
        tab.timestamps[0]
        == time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(start + 2.0)) + tab.timestamps[0][19:]
    )
    tab.on_data_received(9.0, "g", start - 1.0)  # read before Start Recording: ignored
    assert len(tab.times_sec) == 2
    tab.toggle_record()


# --- config.json ---------------------------------------------------------------------------------


def test_config_is_not_rewritten_on_every_reading(window, monkeypatch):
    window.config["known_balances"][window.tab_objects[0].tab_name] = {"brand": "Bonvoisin", "port": ""}
    saves = []
    monkeypatch.setattr(window, "save_config", lambda: saves.append(1))
    tab = window.tab_objects[0]
    tab.toggle_record()
    for i in range(20):
        tab.on_data_received(10.0 + i, "g", tab.start_time + 1.0 + i)
    tab.toggle_record()
    assert len(tab.times_sec) == 20
    assert len(saves) == 1  # once, when the tab first had unsaved readings


# --- don't lose readings without asking --------------------------------------------------------


def _answer(monkeypatch, button_text):
    """Make the next QMessageBox click the button with this text (or Cancel)."""

    def exec_(box):
        for b in box.buttons():
            if b.text().replace("&", "") == button_text:
                b.click()
                return 0
        box.button(QMessageBox.StandardButton.Cancel).click()
        return 0

    monkeypatch.setattr(QMessageBox, "exec", exec_)


def test_closing_while_recording_asks_first(window, monkeypatch):
    window.ask_before_closing = True
    tab = window.tab_objects[0]
    tab.recording = True
    assert "Recording is running" in window.recording_warning()

    _answer(monkeypatch, "Cancel")
    event = QCloseEvent()
    window.closeEvent(event)
    assert not event.isAccepted()  # still open

    _answer(monkeypatch, "Close Anyway")
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted()
    tab.recording = False


def test_unsaved_readings_are_mentioned(window):
    tab = window.tab_objects[0]
    tab.times_sec.append(1.0)
    tab.unsaved_changes = True
    assert "Not saved to Excel yet" in window.recording_warning()
    tab.unsaved_changes = False
    assert window.recording_warning() == ""


def test_clear_data_asks_when_readings_are_not_saved(window, monkeypatch):
    window.ask_before_closing = True
    tab = window.tab_objects[0]
    tab.times_sec.extend([1.0, 2.0])
    tab.unsaved_changes = True
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Cancel)
    tab.request_clear_data()
    assert tab.times_sec == [1.0, 2.0]
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    tab.request_clear_data()
    assert tab.times_sec == [] and not tab.unsaved_changes


# --- the serial reader ---------------------------------------------------------------------------


def test_reader_times_readings_and_closes_its_own_port(qapp, monkeypatch, caplog):
    loop = serial.serial_for_url("loop://", timeout=0.1)
    monkeypatch.setattr(serial_worker.serial, "Serial", lambda **kwargs: loop)
    worker = serial_worker.SerialWorker("loop://", 9600, "Bonvoisin")
    got = []
    worker.data_received.connect(lambda value, unit, when: got.append((value, unit, when)))
    worker.start()
    before = time.time()
    loop.write(b"  12.345 g\r\n")
    deadline = time.time() + 3
    while not got and time.time() < deadline:
        qapp.processEvents()
        time.sleep(0.02)
    worker.stop()
    assert worker.wait(3000)
    assert got and got[0][:2] == (12.345, "g") and got[0][2] >= before - 0.01
    assert not loop.is_open  # closed by the reader thread itself
    assert "failed" not in caplog.text


def test_stopping_a_reader_that_never_started_closes_the_port(monkeypatch):
    loop = serial.serial_for_url("loop://", timeout=0.1)
    monkeypatch.setattr(serial_worker.serial, "Serial", lambda **kwargs: loop)
    worker = serial_worker.SerialWorker("loop://", 9600, "Bonvoisin")
    worker.stop()
    assert not loop.is_open


# --- logs, desktop folder, requirements ------------------------------------------------------------


def test_each_computer_logs_to_its_own_folder():
    from balance_streamer import logs

    assert os.path.basename(logs.LOG_DIR) == computer_folder_name()
    assert os.path.basename(os.path.dirname(logs.LOG_DIR)) == "logs"
    assert computer_folder_name() and "/" not in computer_folder_name() and "\\" not in computer_folder_name()


def test_clean_exit_is_noted_in_the_fatal_log(tmp_path, monkeypatch):
    import crash_log
    from balance_streamer import logs

    monkeypatch.setattr(crash_log, "log_path", lambda: str(tmp_path / "balance_streamer.log"))
    logs.note_clean_exit()
    assert "exited normally" in (tmp_path / "balance_streamer.fatal.log").read_text(encoding="utf-8")


def test_no_desktop_folder_is_not_an_error(monkeypatch):
    from balance_streamer import shortcut
    from balance_streamer.shortcut_panel import ShortcutPanel

    def no_desktop():
        raise shortcut.ShortcutError("Couldn't find your desktop folder (/nowhere).")

    monkeypatch.setattr(shortcut, "desktop_folder", no_desktop)
    assert ShortcutPanel._startup_work(lambda _: None)[0] == "no-desktop"


def test_requirements_do_not_install_pyinstaller():
    with open(os.path.join(REPO_DIR, "requirements.txt"), encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    assert lines == ["-e ."]
