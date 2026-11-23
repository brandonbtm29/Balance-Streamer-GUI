"""The Detect button: which balance is on a port (detect.py), with pretend balances."""

import contextlib
import os
import time
from types import SimpleNamespace

import pytest
import serial.tools.list_ports
from PyQt6.QtCore import QEventLoop, QTimer

from balance_streamer import balance_tab, detect
from balance_streamer.detect import (
    NEVER_SENT,
    Detection,
    DetectionCancelled,
    Detector,
    classify_lines,
    save_sample,
)
from balance_streamer.paths import CONFIG_DIR


class FakeBalance:
    """A pretend balance behind a serial port.

    It works at ``speed``: there it sends ``continuous`` lines on its own (one per read) and
    answers the commands in ``answers``. At any other speed it sends ``noise`` (if it sends
    anything) and understands nothing.
    """

    def __init__(self, speed=9600, continuous=(), answers=None, noise=b"\xf8\x00\x86\x9e"):
        self.speed = speed
        self.continuous = list(continuous)
        self.answers = answers or {}
        self.noise = noise
        self.baudrate = None
        self.written = []
        self.pending = bytearray()
        self.closed = False
        self._next = 0

    def read(self, n):
        if self.continuous:
            if self.baudrate == self.speed:
                self.pending += self.continuous[self._next % len(self.continuous)]
                self._next += 1
            else:
                self.pending += self.noise
        out = bytes(self.pending[:n])
        del self.pending[:n]
        if not out:
            time.sleep(0.001)
        return out

    def write(self, data):
        self.written.append((self.baudrate, data))
        if self.baudrate == self.speed and data in self.answers:
            self.pending += self.answers[data]

    def reset_input_buffer(self):
        self.pending.clear()

    def close(self):
        self.closed = True

    def sent_bytes(self):
        return [data for _, data in self.written]


def _detector(balance, **kwargs):
    def opener(port, baud):
        balance.baudrate = baud
        return balance

    timing = {"listen_s": 0.05, "reply_s": 0.03, "other_listen_s": 0.04, "other_reply_s": 0.02}
    timing.update(kwargs)
    return Detector("COM5", opener=opener, **timing)


def _never_tares_or_calibrates(balance):
    for data in balance.sent_bytes():
        plain = bytes(b & 0x7F for b in data).strip()
        assert plain not in NEVER_SENT, plain


def seven_bit(text):
    return bytes(b | 0x80 for b in text)


@pytest.fixture(autouse=True)
def _no_settings_left_behind():
    """Closing a test window saves config.json; remove it so later tests start fresh."""
    yield
    with contextlib.suppress(FileNotFoundError):
        os.remove(os.path.join(CONFIG_DIR, "config.json"))


# --- listening: balances that send readings on their own --------------------------------------


def test_bonvoisin_is_heard_without_sending_anything():
    balance = FakeBalance(continuous=[b"+0012.34 g\r\n", b"+0012.35 g\r\n"])
    result = _detector(balance).run()
    assert result.brand == "Bonvoisin"
    assert not result.certain
    assert result.guide == "Bonvoisin"
    assert result.sent == [] and balance.written == []
    assert balance.closed
    assert result.heard_anything


def test_lachoi_by_its_three_decimals_or_its_model_letter():
    by_decimals = _detector(FakeBalance(continuous=[b"  +12.345 g\r\n"])).run()
    assert by_decimals.brand == "Lachoi"
    by_letter = _detector(FakeBalance(continuous=[b"N    +12.34 g\r\n"])).run()
    assert by_letter.brand == "Lachoi"


def test_mettler_in_continuous_mode_is_certain():
    result = _detector(FakeBalance(continuous=[b"S D      12.345 g\r\n"])).run()
    assert (result.brand, result.certain) == ("Mettler Toledo", True)


def test_one_line_or_mostly_garbage_is_not_enough_to_judge():
    assert classify_lines(["+12.34 g"]) is None
    assert classify_lines(["+12.34 g", "+12.35 g", "@#!", "~~", "&&", "??"]) is None
    assert classify_lines(["+12.34 g", "+12.35 g"])[0] == "Bonvoisin"


# --- asking: balances that only answer ------------------------------------------------------------


def test_quiet_mettler_answers_and_gives_its_model():
    balance = FakeBalance(answers={b"SI\r\n": b"S S      12.345 g\r\n", b"I2\r\n": b'I2 A "XS204DR"\r\n'})
    result = _detector(balance).run()
    assert (result.brand, result.certain, result.model) == ("Mettler Toledo", True, "XS204DR")
    assert balance.sent_bytes() == [b"SI\r\n", b"I2\r\n"]  # stopped as soon as it knew
    assert "XS204DR" in result.summary


def test_quiet_ohaus_answers_ip():
    balance = FakeBalance(
        answers={b"SI\r\n": b"ES\r\n", b"I2\r\n": b"ES\r\n", b"IP\r\n": b"     12.34 g  \r\n"}
    )
    result = _detector(balance).run()
    assert (result.brand, result.certain) == ("Ohaus Adventurer", True)
    assert b"P\r\n" not in balance.sent_bytes()
    _never_tares_or_calibrates(balance)


def test_ohaus_that_only_knows_p_is_not_offered_as_usable():
    balance = FakeBalance(answers={b"P\r\n": b"     12.34 g\r\n"})
    result = _detector(balance).run()
    assert result.brand is None
    assert result.guide == "Ohaus Adventurer"
    assert "answers P but not IP" in result.summary


def test_listening_comes_before_any_command():
    """A balance that talks on its own never gets a command (a MyWeigh takes P as percent mode)."""
    balance = FakeBalance(continuous=[b"+123.45 g\r\n"], answers={b"P\r\n": b"oops\r\n"})
    _detector(balance).run()
    assert balance.written == []


def test_nothing_at_all():
    balance = FakeBalance()
    result = _detector(balance).run()
    assert result.brand is None
    assert "Nothing came back" in result.summary
    assert not result.heard_anything
    _never_tares_or_calibrates(balance)
    speeds = {baud for baud, _ in balance.written}
    assert speeds == {9600, *detect.OTHER_BAUDS}


def test_command_errors_only_points_to_host_mode():
    balance = FakeBalance(answers={q[1]: b"ES\r\n" for q in detect.QUESTIONS})
    result = _detector(balance).run()
    assert result.brand is None
    assert "not with a weight" in result.summary
    assert result.guide == "Mettler Toledo"


# --- other speeds ---------------------------------------------------------------------------------


def test_balance_at_another_speed_is_told_to_change_it():
    balance = FakeBalance(speed=2400, continuous=[b"+0012.34 g\r\n"])
    result = _detector(balance).run()
    assert result.brand is None  # the app can't read it at 2400
    assert result.baud == 2400
    assert result.guide == "Bonvoisin"
    assert "2400 baud" in result.summary and "9600" in result.summary
    assert balance.written == []  # it was talking, so nothing was sent


def test_ohaus_ar_at_its_factory_setting_is_found_with_seven_bit_questions():
    """2400 baud, 7 data bits, 2 stop bits: questions go out with the top bit set, answers come back so too."""
    balance = FakeBalance(speed=2400, answers={seven_bit(b"P\r\n"): seven_bit(b"   12.34 g\r\n")})
    result = _detector(balance).run()
    assert (result.brand, result.baud, result.guide) == (None, 2400, "Ohaus Adventurer")
    _never_tares_or_calibrates(balance)


# --- cancel, capture, samples ---------------------------------------------------------------------


def test_cancel_stops_it():
    balance = FakeBalance()
    with pytest.raises(DetectionCancelled):
        _detector(balance, cancelled=lambda: True).run()
    assert balance.closed


def test_capture_only_listens():
    balance = FakeBalance(continuous=[b"+0012.34 g\r\n"])
    result = _detector(balance).capture(0.05)
    assert balance.written == []
    assert result.brand == "Bonvoisin"
    assert result.summary.startswith("Recorded")


def test_save_sample_keeps_the_exact_bytes(data_dir):
    result = Detection(summary="test", heard={9600: b"+12.34 g\r\n\x00odd\r\n"}, sent=["SI at 9600 baud"])
    path = save_sample(result, "/dev/cu.usbserial-A1")
    try:
        assert os.path.dirname(os.path.dirname(path)) == os.path.abspath(detect.SAMPLES_FOLDER)
        text = open(path, encoding="utf-8").read()
        assert "b'+12.34 g\\r\\n'" in text and "b'\\x00odd\\r\\n'" in text
        assert "SI at 9600 baud" in text
        assert os.path.basename(path).endswith(" dev-cu.usbserial-A1.txt")
    finally:
        os.remove(path)


# --- the button in a balance tab ------------------------------------------------------------------


def _process_until(condition, ms=3000):
    loop = QEventLoop()
    deadline = time.monotonic() + ms / 1000
    while not condition() and time.monotonic() < deadline:
        QTimer.singleShot(20, loop.quit)
        loop.exec()
    assert condition()


def _with_port(monkeypatch, tab, name="COM5"):
    monkeypatch.setattr(serial.tools.list_ports, "comports", lambda *a, **k: [SimpleNamespace(device=name)])
    tab.refresh_com_ports()
    tab.combo_com.setCurrentText(name)


def _fake_detector(monkeypatch, result):
    class FakeDetector:
        def __init__(self, port, cancelled):
            self.port = port

        def run(self, progress):
            progress("checking")
            return result

        def capture(self, seconds, progress):
            return result

    monkeypatch.setattr(balance_tab, "Detector", FakeDetector)


def test_detect_button_offers_the_brand_and_connects(tab, monkeypatch, data_dir):
    _with_port(monkeypatch, tab)
    found = Detection(
        summary="It sends readings", brand="Lachoi", guide="Lachoi", heard={9600: b"+1.234 g\r\n"}
    )
    _fake_detector(monkeypatch, found)
    shown = []
    monkeypatch.setattr(tab, "_detection_choice", lambda result, port, sample: shown.append(sample) or "use")
    connected = []
    monkeypatch.setattr(tab, "connect_serial", lambda auto=False: connected.append(auto))
    tab.combo_brand.setCurrentText("Bonvoisin")
    tab.detect_brand()
    _process_until(lambda: tab._detect_task is None)
    assert tab.combo_brand.currentText() == "Lachoi"
    assert connected == [False]
    assert tab.btn_detect.isEnabled() and tab.btn_connect.isEnabled()
    assert shown[0] and os.path.exists(shown[0])  # what it heard was saved
    os.remove(shown[0])


def test_detect_reconnects_as_before_when_closed(tab, monkeypatch):
    _with_port(monkeypatch, tab)
    _fake_detector(monkeypatch, Detection(summary="Nothing came back."))
    monkeypatch.setattr(tab, "_detection_choice", lambda *a: "close")
    tab.serial_thread = SimpleNamespace(
        port="COM5", isRunning=lambda: True, stop=lambda: None, wait=lambda: True
    )
    connected = []
    monkeypatch.setattr(tab, "connect_serial", lambda auto=False: connected.append(auto))
    tab.detect_brand()
    assert tab.serial_thread is None  # let go of the port first
    _process_until(lambda: tab._detect_task is None)
    assert connected == [True]


def test_detect_opens_the_guide(window, monkeypatch):
    tab = window.tab_objects[0]
    _with_port(monkeypatch, tab)
    _fake_detector(monkeypatch, Detection(summary="x", guide="Ohaus Adventurer"))
    monkeypatch.setattr(tab, "_detection_choice", lambda *a: "guide")
    tab.detect_brand()
    _process_until(lambda: tab._detect_task is None)
    assert window.tabs.currentWidget() is window.settings_tab
    guides = window.settings_tab.guides_page
    assert guides.tabs.currentWidget() is guides.pages["Ohaus Adventurer"]


def test_detect_refuses_a_port_another_tab_uses(window, monkeypatch):
    first = window.tab_objects[0]
    window.add_tab("Second")
    second = window.tab_objects[1]
    _with_port(monkeypatch, second)
    first.serial_thread = SimpleNamespace(port="COM5", isRunning=lambda: True, stop=lambda: None)
    warned = []
    monkeypatch.setattr(balance_tab.QMessageBox, "warning", lambda *a: warned.append(a[2]))
    second.detect_brand()
    assert second._detect_task is None
    assert "in use by the tab" in warned[0]
    first.serial_thread = None


def test_detect_needs_a_port(tab, monkeypatch):
    told = []
    monkeypatch.setattr(balance_tab.QMessageBox, "information", lambda *a: told.append(a[2]))
    tab.combo_com.clear()
    tab.detect_brand()
    assert told and tab._detect_task is None


def test_a_port_that_cant_be_opened_is_reported(tab, monkeypatch):
    _with_port(monkeypatch, tab)

    class Busy:
        def __init__(self, port, cancelled):
            pass

        def run(self, progress):
            raise serial.SerialException("Access is denied.")

    monkeypatch.setattr(balance_tab, "Detector", Busy)
    warned = []
    monkeypatch.setattr(balance_tab.QMessageBox, "warning", lambda *a: warned.append(a[2]))
    tab.detect_brand()
    _process_until(lambda: tab._detect_task is None)
    assert "Access is denied" in warned[0]
