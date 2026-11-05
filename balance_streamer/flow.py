"""Turning logged mass into flow rates."""

import datetime
import logging

import numpy as np
import scipy.signal

log = logging.getLogger(__name__)


class FlowMixin:
    """Part of BalanceTab: turning logged mass into flow rates."""

    def calculate_flows(self):
        n = len(self.times_sec)
        while len(self.flow_rates) < n:
            self.flow_rates.append(None)

        if n < 2:
            return
        deriv_raw = None
        if n >= 5:
            try:
                sg_win = max(5, int(self.ent_savgol_win.text()))
                if sg_win % 2 == 0:
                    sg_win += 1
                sg_poly = min(sg_win - 1, int(self.ent_savgol_poly.text()))

                if n >= sg_win:
                    w_sm = scipy.signal.savgol_filter(self.weights, window_length=sg_win, polyorder=sg_poly)
                    deriv_raw = np.gradient(w_sm, self.times_sec)
            except Exception:  # bad Savitzky-Golay settings: fall back to the plain derivative
                log.debug("Savitzky-Golay derivative failed; using np.gradient", exc_info=True)
        if deriv_raw is None:
            deriv_raw = np.gradient(self.weights, self.times_sec)
        raw = np.asarray(deriv_raw, dtype=float) * 60.0  # g/s -> g/min

        filter_type = self.combo_filter.currentText()
        # The smoothing below works on whole numpy arrays: the same maths as before, done in
        # compiled code. The old per-point Python loops took seconds per new reading on long
        # runs, which froze the window.

        if filter_type in ["Mean", "Median"]:
            try:
                win = max(1, int(self.ent_filter_param.text()))
            except ValueError:
                win = 20
            self._set_window_average(raw, win, median=(filter_type == "Median"))

        elif filter_type == "EMA":
            try:
                alpha = float(self.ent_filter_param.text())
            except ValueError:
                alpha = 0.1
            alpha = max(0.01, min(1.0, alpha))

            # y[0] = x[0]; y[i] = alpha * x[i] + (1 - alpha) * y[i - 1]
            ema = scipy.signal.lfilter([alpha], [1.0, -(1.0 - alpha)], raw, zi=[(1.0 - alpha) * raw[0]])[0]
            self.flow_rates[:n] = ema.tolist()

        elif filter_type == "Butterworth":
            try:
                cutoff = float(self.ent_filter_param.text())
            except ValueError:
                cutoff = 0.05

            try:
                try:
                    intrvl = float(self.ent_interval.text())
                except ValueError:
                    intrvl = 1.0
                fs = 1.0 / max(0.1, intrvl)
                nyq = 0.5 * fs
                normal_cutoff = cutoff / nyq

                if n > 15 and normal_cutoff < 1.0:
                    b, a = scipy.signal.butter(2, normal_cutoff, btype="low", analog=False)
                    self.flow_rates[:n] = scipy.signal.filtfilt(b, a, raw).tolist()
                else:
                    self.flow_rates[:n] = raw.tolist()
            except Exception:  # filter failed: show the unfiltered flow rather than nothing
                log.debug("Butterworth filter failed; showing unfiltered flow", exc_info=True)
                self.flow_rates[:n] = raw.tolist()

        elif filter_type == "Adaptive":
            try:
                rpm = float(self.ent_rpm.text())
            except ValueError:
                rpm = 30.0
            if rpm <= 0:
                rpm = 1.0
            try:
                rollers = float(self.ent_rollers.text())
            except ValueError:
                rollers = 3.0
            if rollers <= 0:
                rollers = 1.0

            pulse_hz = (rpm / 60.0) * rollers
            period_sec = 1.0 / pulse_hz
            try:
                intrvl = float(self.ent_interval.text())
            except ValueError:
                intrvl = 1.0
            win = max(1, int(round(period_sec / max(0.1, intrvl))))
            self._set_window_average(raw, win, median=False)

    def _set_window_average(self, raw, win, median):
        """flow_rates[i] = mean (or median) of raw[i - win + 1 .. i], for every i >= win - 1.

        Points before the first full window keep whatever value they had, as before.
        """
        n = len(raw)
        if n < win:
            return
        windows = np.lib.stride_tricks.sliding_window_view(raw, win)
        values = np.median(windows, axis=1) if median else windows.mean(axis=1)
        self.flow_rates[win - 1 : n] = values.tolist()

    def get_wall_clock_data(self):
        if not hasattr(self, "wall_clock_min"):
            self.wall_clock_min = []

        if len(self.wall_clock_min) < len(self.timestamps):
            # Time stamps look like "2026-01-15 10:00:00.000"; fromisoformat also reads them
            # without the milliseconds. (strptime without ".%f" used to fail on every one,
            # so the Timestamp axis silently showed Duration instead.)
            try:
                if len(self.wall_clock_min) == 0:
                    self._t0 = datetime.datetime.fromisoformat(self.timestamps[0])
                for i in range(len(self.wall_clock_min), len(self.timestamps)):
                    t = datetime.datetime.fromisoformat(self.timestamps[i])
                    self.wall_clock_min.append((t - self._t0).total_seconds() / 60.0)
            except ValueError:
                log.warning("Unreadable time stamp; showing duration on the time axis", exc_info=True)
                while len(self.wall_clock_min) < len(self.timestamps):
                    self.wall_clock_min.append(self.times_min[len(self.wall_clock_min)])
        return self.wall_clock_min
