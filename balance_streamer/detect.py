"""Find out which kind of balance is on a serial port: the Detect button next to the Brand box.

Safest first:

1. Listen without sending anything. Bonvoisin, Lachoi, MyWeigh and Adam balances in continuous mode
   send readings on their own, and the shape of their lines tells them apart. That part is a best
   guess; the app reads all of them the same way, so it mainly decides which guide is offered.
2. Only if the balance stays quiet, ask it: the Mettler Toledo commands "send the weight now" (SI)
   and "which model are you" (I2), then the Ohaus print commands (IP for newer Adventurers, P for
   the AR series). Nothing else is ever sent: no tare, no calibration. Listening comes first because
   a MyWeigh balance takes P as "percent mode" and C as "calibrate".
3. If nothing answers at 9600 baud, or what comes is garbled, try the other common speeds. The app
   reads only 9600 baud, 8 data bits, no parity, 1 stop bit, so a balance found at another speed is
   told to change its speed instead of being given a brand.

What the balance sent is kept (``Detection.heard``) and can be saved with :func:`save_sample`, so
these rules can be checked against real balances. The rules for lines heard without asking come
from the manuals and the Bonvoisin menu guide, not yet from recorded output.
"""

import os
import re
import time
from collections import Counter
from dataclasses import dataclass, field

import serial

from . import __version__
from .paths import computer_folder_name

APP_BAUD = 9600
OTHER_BAUDS = (2400, 4800, 19200, 1200)  # 2400 is the Ohaus AR's factory setting
SAMPLES_FOLDER = "Balance samples"  # in the data folder, one subfolder per computer

# A reading: a number, then a unit ("+123.45 g", "  12.345 g", "S S   0.123 g").
NUMBER_UNIT = re.compile(r"([+-]?\s*\d+(?:\.(\d+))?)\s*([a-zA-Z%]+)")
# Mettler Toledo (MT-SICS) answers to SI: S S (stable), S D (changing), S I (busy), S + / S - (over/under).
METTLER_WEIGHT = re.compile(r"^S\s+[SDI+-](?:\s|$)")
METTLER_MODEL = re.compile(r'^I2\s+A\s+"?([^"]*)"?')
COMMAND_ERROR = re.compile(r"^E[STL]$")  # ES, ET, EL: "didn't understand that command"
# Lachoi manual: a model character, spaces, then the sign and the digits.
LACHOI_LINE = re.compile(r"^[A-Za-z]\s+[+-]?\s*\d")

# (who understands it, command, what it asks). Only read or identify commands.
QUESTIONS = (
    ("Mettler Toledo", b"SI\r\n", "SI (Mettler: send the weight)"),
    ("Mettler Toledo", b"I2\r\n", "I2 (Mettler: model)"),
    ("Ohaus Adventurer", b"IP\r\n", "IP (Ohaus: print now)"),
    ("Ohaus Adventurer", b"P\r\n", "P (Ohaus AR: print)"),
)
NEVER_SENT = (b"T", b"C", b"Z")  # tare, calibrate, zero: checked by the tests


def as_seven_bit(question):
    """The same question for a balance set to 7 data bits and 2 stop bits (the Ohaus AR's factory
    setting): with the top bit set, each byte ends in the two stop bits that balance expects."""
    brand, command, description = question
    return brand, bytes(b | 0x80 for b in command), description + ", 7 data bits"


# At other speeds: one Mettler and the Ohaus questions, also as 7-bit data.
OTHER_SPEED_QUESTIONS = (QUESTIONS[0], QUESTIONS[2], as_seven_bit(QUESTIONS[2]), as_seven_bit(QUESTIONS[3]))


class DetectionCancelled(Exception):
    pass


@dataclass
class Detection:
    """What Detect found. ``brand`` is a name from the Brand box, or None if the app can't use it as is."""

    summary: str
    brand: str | None = None
    certain: bool = False
    guide: str = "Start here"  # Balance Guides page to offer
    baud: int | None = None  # the speed it answered at
    model: str = ""
    sent: list = field(default_factory=list)  # descriptions of the commands sent
    heard: dict = field(default_factory=dict)  # baud -> raw bytes received

    @property
    def heard_anything(self):
        return any(self.heard.values())


def open_port(port, baud):
    """Open ``port`` the way the app reads balances (8 data bits, no parity, 1 stop bit)."""
    return serial.Serial(
        port=port,
        baudrate=baud,
        timeout=0.05,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    )


def text_lines(raw):
    """The non-empty lines in ``raw``. The top bit is dropped, so 7-bit data read as 8 still shows."""
    text = bytes(b & 0x7F for b in raw).decode("ascii", errors="ignore")
    return [line.strip() for line in re.split(r"[\r\n]+", text) if line.strip()]


def readable(lines):
    """Lines that hold a number and a unit."""
    return [line for line in lines if NUMBER_UNIT.search(line)]


def decimals(line):
    match = NUMBER_UNIT.search(line)
    return len(match.group(2)) if match and match.group(2) else 0


def classify_lines(lines, min_readings=2):
    """Brand, certainty and reason for readings a balance sent on its own; None if they don't read
    as weights (fewer than ``min_readings`` readable lines, or mostly unreadable ones)."""
    readings = readable(lines)
    if len(readings) < min_readings or len(readings) * 2 < len(lines):
        return None
    if any(METTLER_WEIGHT.match(line) for line in readings):
        return "Mettler Toledo", True, "It sends Mettler Toledo (MT-SICS) readings on its own."
    places = Counter(decimals(line) for line in readings).most_common(1)[0][0]
    if sum(1 for line in readings if LACHOI_LINE.match(line)) * 2 >= len(readings):
        return "Lachoi", False, "Its lines start with a model letter, as a Lachoi's do."
    if places == 3:
        return "Lachoi", False, "It sends readings on its own to 0.001 g, like the Lachoi JT503D."
    return (
        "Bonvoisin",
        False,
        f"It sends readings on its own to {places} decimal places, like the Bonvoisin. MyWeigh and "
        "Adam balances look the same and use the Bonvoisin setting too.",
    )


class Detector:
    """Runs the checks on one port. Every wait is a parameter so the tests can run fast."""

    def __init__(
        self,
        port,
        *,
        opener=open_port,
        cancelled=lambda: False,
        listen_s=2.0,
        reply_s=0.8,
        other_listen_s=1.5,
        other_reply_s=0.5,
        enough_lines=6,
        other_bauds=OTHER_BAUDS,
    ):
        self.port = port
        self.opener = opener
        self.cancelled = cancelled
        self.listen_s = listen_s
        self.reply_s = reply_s
        self.other_listen_s = other_listen_s
        self.other_reply_s = other_reply_s
        self.enough_lines = enough_lines
        self.other_bauds = other_bauds
        self.sent = []
        self.heard = {}

    # --- talking to the port -----------------------------------------------------------------

    def _check_cancelled(self):
        if self.cancelled():
            raise DetectionCancelled

    def _listen(self, ser, baud, seconds, enough_lines=None):
        """Bytes received in ``seconds`` (sooner once ``enough_lines`` readable lines arrived)."""
        data = bytearray()
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._check_cancelled()
            chunk = ser.read(256)
            if chunk:
                data += chunk
                if enough_lines and len(readable(text_lines(data))) >= enough_lines:
                    break
        self.heard[baud] = self.heard.get(baud, b"") + bytes(data)
        return bytes(data)

    def _ask(self, ser, baud, command, description, seconds):
        """Send one read/identify command; the first line of the answer ("" if none)."""
        self._check_cancelled()
        ser.reset_input_buffer()
        ser.write(command)
        self.sent.append(f"{description} at {baud} baud")
        data = bytearray()
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._check_cancelled()
            chunk = ser.read(256)
            if chunk:
                data += chunk
                if re.search(rb"[\r\n]", bytes(c & 0x7F for c in data)) and text_lines(data):
                    break  # a whole line came back (a 7-bit balance's line ends read as 0x8D/0x8A)
        self.heard[baud] = self.heard.get(baud, b"") + bytes(data)
        lines = text_lines(data)
        return lines[0] if lines else ""

    def _result(self, summary, **kwargs):
        return Detection(summary=summary, sent=list(self.sent), heard=dict(self.heard), **kwargs)

    # --- the checks --------------------------------------------------------------------------

    def _ask_questions(self, ser, baud, seconds, questions=QUESTIONS):
        """Ask in order; (brand, certain, reason, model, ohaus_command) for the first real answer."""
        answered_error = False
        for brand, command, description in questions:
            reply = self._ask(ser, baud, command, description, seconds)
            if not reply:
                continue
            if brand == "Mettler Toledo":
                if METTLER_WEIGHT.match(reply):
                    model = ""
                    if command.startswith(b"SI"):
                        model_reply = self._ask(ser, baud, b"I2\r\n", "I2 (Mettler: model)", seconds)
                        found = METTLER_MODEL.match(model_reply)
                        model = found.group(1).strip() if found else ""
                    return brand, True, "It answered the Mettler Toledo command for a reading.", model, None
                found = METTLER_MODEL.match(reply)
                if found:
                    return brand, True, "It told us its Mettler Toledo model.", found.group(1).strip(), None
            elif NUMBER_UNIT.search(reply) and not reply.startswith(("S ", "ES")):
                return (
                    brand,
                    True,
                    "It answered the Ohaus print command.",
                    "",
                    bytes(b & 0x7F for b in command).strip().decode(),
                )
            if COMMAND_ERROR.match(reply):
                answered_error = True
        return None, False, "answers commands, but not with a weight" if answered_error else "", "", None

    def run(self, progress=lambda text: None):
        """Check the port and say what's on it. Raises DetectionCancelled, or serial errors on open."""
        ser = self.opener(self.port, APP_BAUD)
        try:
            return self._run(ser, progress)
        finally:
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass

    def _run(self, ser, progress):
        progress(f"Listening to {self.port} (nothing is sent)...")
        heard = self._listen(ser, APP_BAUD, self.listen_s, self.enough_lines)
        found = classify_lines(text_lines(heard))
        if heard and not found:  # something came, but not enough to judge: a slow sender?
            heard += self._listen(ser, APP_BAUD, self.listen_s, self.enough_lines)
            found = classify_lines(text_lines(heard))
        if found:
            brand, certain, reason = found
            return self._result(reason, brand=brand, certain=certain, guide=brand, baud=APP_BAUD)
        garbled = bool(heard)

        command_error = False
        if not garbled:
            progress("It sent nothing on its own. Asking it for a reading...")
            brand, certain, reason, model, ohaus_command = self._ask_questions(ser, APP_BAUD, self.reply_s)
            if brand == "Ohaus Adventurer" and ohaus_command == "P":
                return self._result(
                    "An Ohaus balance that answers P but not IP (probably the Adventurer AR series). "
                    "The app asks with IP, so it can't read this balance yet: tell whoever looks after "
                    "the app.",
                    guide="Ohaus Adventurer",
                    baud=APP_BAUD,
                )
            if brand:
                summary = reason + (f" Model: {model}." if model else "")
                return self._result(
                    summary, brand=brand, certain=certain, guide=brand, baud=APP_BAUD, model=model
                )
            command_error = bool(reason)

        for baud in self.other_bauds:
            progress(f"Trying {baud} baud...")
            ser.baudrate = baud
            ser.reset_input_buffer()
            other = self._listen(ser, baud, self.other_listen_s, self.enough_lines)
            found = classify_lines(text_lines(other))
            guess = found[0] if found else None
            if not found and not other:
                guess, *_ = self._ask_questions(ser, baud, self.other_reply_s, OTHER_SPEED_QUESTIONS)
            if guess:
                return self._result(
                    f"It answers at {baud} baud, but the app reads only {APP_BAUD} baud (8 data bits, no "
                    f"parity, 1 stop bit). Set the balance to {APP_BAUD} baud in its menu. It "
                    f"looks like this brand: {guess}.",
                    guide=guess,
                    baud=baud,
                )

        if garbled:
            return self._result(
                f"It sends something, but it's garbled at every speed tried. The balance's baud rate, "
                f"data bits or stop bits probably don't match {APP_BAUD} baud, 8 data bits, no parity, "
                f"1 stop bit; the cable may also be wrong."
            )
        if command_error:
            return self._result(
                "Something answers commands, but not with a weight. A Mettler Toledo may be in Printer "
                "mode instead of Host mode, or this is a brand the app doesn't know.",
                guide="Mettler Toledo",
            )
        return self._result(
            "Nothing came back. Check that the balance is on, that its RS-232 output is on (continuous "
            "output for Bonvoisin and Lachoi, Host mode for Mettler Toledo) and that it's the right cable."
        )

    def capture(self, seconds, progress=lambda text: None):
        """Listen for ``seconds`` at 9600 baud without sending anything, for a sample file."""
        ser = self.opener(self.port, APP_BAUD)
        try:
            progress(f"Recording what {self.port} sends for {seconds:g} s (nothing is sent)...")
            heard = self._listen(ser, APP_BAUD, seconds)
        finally:
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass
        lines = text_lines(heard)
        found = classify_lines(lines)
        summary = f"Recorded {seconds:g} s: {len(heard)} bytes, {len(lines)} lines."
        if found:
            brand, certain, reason = found
            return self._result(
                f"{summary} {reason}", brand=brand, certain=certain, guide=brand, baud=APP_BAUD
            )
        return self._result(summary + (" None of it reads as a weight." if heard else " Nothing came."))


def save_sample(detection, port, folder=SAMPLES_FOLDER):
    """Write what the balance sent to ``<folder>/<computer>/<date time> <port>.txt``; its path."""
    safe_port = re.sub(r"[^A-Za-z0-9._-]+", "-", port).strip("-") or "port"
    directory = os.path.join(folder, computer_folder_name())
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{time.strftime('%Y-%m-%d %H%M%S')} {safe_port}.txt")
    out = [
        f"Balance Streamer {__version__} - what {port} sent",
        f"When: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Result: {detection.summary}",
        f"Brand: {detection.brand or '-'} ({'certain' if detection.certain else 'best guess'})",
        "Sent: " + ("; ".join(detection.sent) if detection.sent else "nothing"),
        "",
    ]
    for baud, raw in detection.heard.items():
        out.append(f"--- {baud} baud: {len(raw)} bytes ---")
        out.extend(repr(line) for line in raw.splitlines(keepends=True))
        out.append("")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    return os.path.abspath(path)
