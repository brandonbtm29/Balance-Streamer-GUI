"""Cable memory: a balance's USB-to-serial cable is recognised by its serial number (cables.py)."""

import contextlib
import json
import os
from types import SimpleNamespace

import pytest
import serial.tools.list_ports
from PyQt6.QtCore import QEventLoop, QTimer

from balance_streamer import main_window
from balance_streamer.cables import cable_of, holds_other_cable, port_with_cable, same_cable, usable_cable
from balance_streamer.main_window import MultiBalanceApp, pick_port
from balance_streamer.paths import CONFIG_DIR

FTDI_A = SimpleNamespace(device="COM7", serial_number="A10K1", vid=0x0403, pid=0x6001, manufacturer="FTDI")
FTDI_B = SimpleNamespace(device="COM12", serial_number="B22Q9", vid=0x0403, pid=0x6001, manufacturer="FTDI")
CH340 = SimpleNamespace(device="COM3", serial_number=None, vid=0x1A86, pid=0x7523, manufacturer="wch.cn")
CABLE_A = {"serial_number": "A10K1", "vid": 0x0403, "pid": 0x6001}


@pytest.fixture(autouse=True)
def _no_settings_left_behind():
    """Closing a test window saves config.json; remove it so later tests start fresh."""
    yield
    with contextlib.suppress(FileNotFoundError):
        os.remove(os.path.join(CONFIG_DIR, "config.json"))


def _details(*infos):
    return {info.device: info for info in infos}


def _ports(monkeypatch, *infos):
    monkeypatch.setattr(serial.tools.list_ports, "comports", lambda *a, **k: list(infos))


def test_cable_of():
    assert cable_of(FTDI_A) == {
        "serial_number": "A10K1",
        "vid": 0x0403,
        "pid": 0x6001,
        "manufacturer": "FTDI",
    }
    assert cable_of(CH340) is None  # no serial number: nothing to recognise
    assert cable_of(SimpleNamespace(device="COM1")) is None
    assert cable_of(None) is None
    assert "manufacturer" not in cable_of(SimpleNamespace(device="x", serial_number="1", manufacturer="n/a"))


def test_same_cable_and_where_it_is():
    assert same_cable(cable_of(FTDI_A), CABLE_A)
    assert not same_cable(cable_of(FTDI_B), CABLE_A)
    assert not same_cable({"serial_number": "A10K1", "vid": 1}, CABLE_A)  # another maker's chip
    assert port_with_cable(CABLE_A, _details(FTDI_A, FTDI_B, CH340)) == "COM7"
    assert port_with_cable(CABLE_A, _details(FTDI_B, CH340)) is None
    twin = SimpleNamespace(**{**vars(FTDI_A), "device": "COM8"})  # copies that share a serial number
    assert port_with_cable(CABLE_A, _details(FTDI_A, twin)) is None
    assert holds_other_cable("COM12", CABLE_A, _details(FTDI_B))
    assert not holds_other_cable("COM3", CABLE_A, _details(CH340))
    assert not holds_other_cable("COM9", CABLE_A, {})


def test_a_cable_two_balances_remember_is_not_used():
    known = {
        "C1": {"cable": CABLE_A},
        "Balance 6": {"cable": dict(CABLE_A)},
        "C2": {"cable": {"serial_number": "Z"}},
    }
    assert usable_cable("C1", known) is None
    assert usable_cable("C2", known) == {"serial_number": "Z"}
    assert usable_cable("C3", known) is None


def test_pick_port_follows_the_cable():
    details = _details(FTDI_A, FTDI_B, CH340)
    available = list(details)
    assert pick_port("COM12", "COM12", available, CABLE_A, details) == "COM7"  # moved: follow it
    assert pick_port("COM3", "COM3", available, CABLE_A, _details(FTDI_B, CH340)) == "COM3"  # unknown cable
    assert pick_port("COM12", None, ["COM12"], CABLE_A, _details(FTDI_B)) is None  # another balance's cable
    assert pick_port("COM12", None, ["COM12"]) == "COM12"  # nothing remembered: as before


@contextlib.contextmanager
def _window_with(config):
    config_path = os.path.join(CONFIG_DIR, "config.json")
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f)
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


def _record_opens(monkeypatch):
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


def test_window_connects_where_the_cable_is_now(qapp, monkeypatch):
    _ports(monkeypatch, FTDI_A, FTDI_B)
    opened = _record_opens(monkeypatch)
    config = {"known_balances": {"C1": {"brand": "Lachoi", "port": "COM12", "cable": CABLE_A}}}
    with _window_with(config) as win:
        assert win.tab_objects[0].combo_com.currentText() == "COM7"
        _process_events()
        assert opened == ["COM7"]


def test_window_wont_use_a_port_with_another_balances_cable(qapp, monkeypatch):
    _ports(monkeypatch, FTDI_B)
    opened = _record_opens(monkeypatch)
    config = {"known_balances": {"C1": {"brand": "Lachoi", "port": "COM12", "cable": CABLE_A}}}
    with _window_with(config) as win:
        tab = win.tab_objects[0]
        _process_events()
        assert opened == []
        assert "different cable" in tab.lbl_status.text()


def test_connecting_remembers_the_cable_or_forgets_it(window, monkeypatch):
    _ports(monkeypatch, FTDI_A, CH340)
    window.config["known_balances"]["C1"] = {"brand": "Lachoi", "port": "COM9"}
    window.save_connection("C1", "Lachoi", "COM7")
    assert same_cable(window.config["known_balances"]["C1"]["cable"], CABLE_A)
    window.save_connection("C1", "Lachoi", "COM3")  # moved to a cable without a serial number
    assert "cable" not in window.config["known_balances"]["C1"]
    with open(main_window.WINDOW_STATE_PATH, encoding="utf-8") as f:
        assert json.load(f)["ports"]["C1"] == "COM3"
