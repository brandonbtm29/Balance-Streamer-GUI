"""Turning logged mass into flow rates."""

import datetime
import logging
import statistics

log = logging.getLogger(__name__)


class FlowMixin:
    """Part of BalanceTab: turning logged mass into flow rates."""

    def calculate_flows(self):
        n = len(self.times_sec)
        while len(self.flow_rates) < n:
            self.flow_rates.append(None)

        valid_indices = []
        raw_flows = [None] * n

        if n >= 5:
            try:
                sg_win = max(5, int(self.ent_savgol_win.text()))
                if sg_win % 2 == 0:
                    sg_win += 1
                sg_poly = min(sg_win - 1, int(self.ent_savgol_poly.text()))

                import numpy as np
                import scipy.signal

                if n >= sg_win:
                    w_sm = scipy.signal.savgol_filter(self.weights, window_length=sg_win, polyorder=sg_poly)
                    deriv_raw = np.gradient(w_sm, self.times_sec)
                else:
                    deriv_raw = np.gradient(self.weights, self.times_sec)

                for i in range(n):
                    raw_flows[i] = deriv_raw[i] * 60.0
                    valid_indices.append(i)
            except Exception:  # bad Savitzky-Golay settings: fall back to the plain derivative
                log.debug("Savitzky-Golay derivative failed; using np.gradient", exc_info=True)
                import numpy as np

                deriv_raw = np.gradient(self.weights, self.times_sec)
                for i in range(n):
                    raw_flows[i] = deriv_raw[i] * 60.0
                    valid_indices.append(i)
        elif n > 1:
            import numpy as np

            deriv_raw = np.gradient(self.weights, self.times_sec)
            for i in range(n):
                raw_flows[i] = deriv_raw[i] * 60.0
                valid_indices.append(i)

        if not valid_indices:
            return

        filter_type = self.combo_filter.currentText()

        if filter_type in ["Mean", "Median"]:
            try:
                win = max(1, int(self.ent_filter_param.text()))
            except ValueError:
                win = 20

            for v_idx in range(len(valid_indices)):
                if v_idx >= win - 1:
                    i = valid_indices[v_idx]
                    window_indices = valid_indices[v_idx - win + 1 : v_idx + 1]
                    vals = [raw_flows[idx] for idx in window_indices]
                    if filter_type == "Mean":
                        self.flow_rates[i] = statistics.mean(vals)
                    else:
                        self.flow_rates[i] = statistics.median(vals)

        elif filter_type == "EMA":
            try:
                alpha = float(self.ent_filter_param.text())
            except ValueError:
                alpha = 0.1
            alpha = max(0.01, min(1.0, alpha))

            self.flow_rates[valid_indices[0]] = raw_flows[valid_indices[0]]
            for v_idx in range(1, len(valid_indices)):
                i = valid_indices[v_idx]
                prev_i = valid_indices[v_idx - 1]
                if self.flow_rates[prev_i] is not None:
                    self.flow_rates[i] = alpha * raw_flows[i] + (1 - alpha) * self.flow_rates[prev_i]
                else:
                    self.flow_rates[i] = raw_flows[i]

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

                if len(valid_indices) > 15 and normal_cutoff < 1.0:
                    import scipy.signal

                    b, a = scipy.signal.butter(2, normal_cutoff, btype="low", analog=False)
                    raw_vals = [raw_flows[idx] for idx in valid_indices]
                    filtered_vals = scipy.signal.filtfilt(b, a, raw_vals)
                    for v_idx, val in enumerate(filtered_vals):
                        self.flow_rates[valid_indices[v_idx]] = val
                else:
                    for i in valid_indices:
                        self.flow_rates[i] = raw_flows[i]
            except Exception:  # filter failed: show the unfiltered flow rather than nothing
                log.debug("Butterworth filter failed; showing unfiltered flow", exc_info=True)
                for i in valid_indices:
                    self.flow_rates[i] = raw_flows[i]

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

            for v_idx in range(len(valid_indices)):
                if v_idx >= win - 1:
                    i = valid_indices[v_idx]
                    window_indices = valid_indices[v_idx - win + 1 : v_idx + 1]
                    vals = [raw_flows[idx] for idx in window_indices]
                    self.flow_rates[i] = statistics.mean(vals)

    def get_wall_clock_data(self):
        if not hasattr(self, "wall_clock_min"):
            self.wall_clock_min = []

        if len(self.wall_clock_min) < len(self.timestamps):
            try:
                if len(self.wall_clock_min) == 0:
                    self._t0 = datetime.datetime.strptime(self.timestamps[0], "%Y-%m-%d %H:%M:%S")
                for i in range(len(self.wall_clock_min), len(self.timestamps)):
                    t = datetime.datetime.strptime(self.timestamps[i], "%Y-%m-%d %H:%M:%S")
                    self.wall_clock_min.append((t - self._t0).total_seconds() / 60.0)
            except:
                while len(self.wall_clock_min) < len(self.timestamps):
                    self.wall_clock_min.append(self.times_min[len(self.wall_clock_min)])
        return self.wall_clock_min
