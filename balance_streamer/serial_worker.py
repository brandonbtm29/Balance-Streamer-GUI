"""Background thread that reads one balance. Never touch widgets from this thread."""

import logging
import time

import serial
import serial.tools.list_ports
from PyQt6.QtCore import QThread, pyqtSignal

from .parsers import parse_bonvoisin_response, parse_mt_sics_response, parse_ohaus_response

log = logging.getLogger(__name__)


def available_ports():
    """Names of the serial ports on this computer (COM3, /dev/cu.usbserial-..., ...)."""
    return [p.device for p in serial.tools.list_ports.comports()]


class SerialWorker(QThread):
    # value, unit, and the time.time() at which the line arrived. The time is taken here, in
    # the reading thread, so a busy window can't delay or bunch up the time stamps.
    data_received = pyqtSignal(float, str, float)

    def __init__(self, port, baudrate, brand):
        super().__init__()
        self.port = port
        self.baudrate = baudrate
        self.brand = brand
        self.running = True
        self.ser = None

        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
        except Exception as e:
            self.error_msg = str(e)
            self.running = False

    def run(self):
        try:
            self._read_loop()
        finally:
            # The port is closed here, by the thread that reads it. Closing it from the window
            # while a read was in progress caused "Bad file descriptor" errors (and on Windows
            # closed the handle under a pending read).
            self._close()

    def _read_loop(self):
        while self.running and self.ser and self.ser.is_open:
            try:
                if self.brand == "Mettler Toledo":
                    if self.ser.in_waiting == 0:
                        self.ser.write(b"SI\r\n")
                elif self.brand == "Ohaus Adventurer":
                    if self.ser.in_waiting == 0:
                        self.ser.write(b"IP\r\n")

                response = self.ser.readline()
                read_time = time.time()
                if not self.running:
                    break
                if response:
                    decoded = response.decode("ascii", errors="ignore").strip()
                    if not decoded:
                        continue

                    if self.brand == "Mettler Toledo":
                        status, value, unit = parse_mt_sics_response(decoded)
                    elif self.brand == "Ohaus Adventurer":
                        status, value, unit = parse_ohaus_response(decoded)
                    else:
                        status, value, unit = parse_bonvoisin_response(decoded)

                    if value is not None:
                        self.data_received.emit(value, unit, read_time)
                        self._read_error_logged = False

            except Exception:
                if not self.running:
                    break  # stopping: the read was cancelled on purpose
                # Typically the cable was unplugged or the port went away. Log it once,
                # not ten times a second, and keep trying in case it comes back.
                if not getattr(self, "_read_error_logged", False):
                    log.warning("Reading %s (%s) failed; retrying", self.port, self.brand, exc_info=True)
                    self._read_error_logged = True
                time.sleep(0.1)

    def stop(self):
        """Ask the thread to stop; it closes the port itself. Call wait() afterwards."""
        self.running = False
        if self.isRunning():
            try:
                self.ser.cancel_read()  # end a read in progress now instead of after its timeout
            except (AttributeError, serial.SerialException, OSError):
                pass  # not supported on this platform: the 0.1 s read timeout ends it anyway
        else:
            self._close()  # never started (or already finished): nothing else will close it

    def _close(self):
        if self.ser is not None and self.ser.is_open:
            try:
                self.ser.close()
            except (serial.SerialException, OSError):
                log.warning("Couldn't close %s cleanly", self.port, exc_info=True)

    def send_tare(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b"T\r\n")
            except (serial.SerialException, OSError):
                log.warning("Couldn't send the tare command to %s", self.port, exc_info=True)
