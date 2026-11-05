"""The fast flow maths gives the same numbers as the 1.4.0 code (tests/flow_reference.py)."""

import math
import random
import time

import flow_reference
import pytest

from balance_streamer import flow


class _Box:
    """Stands in for a QLineEdit / QComboBox: only .text() / .currentText() are used."""

    def __init__(self, text):
        self._text = text

    def text(self):
        return self._text

    def currentText(self):
        return self._text


def _tab(module, n, filt, param, savgol=("60", "1"), interval="1.0", rpm="30", rollers="3", stale=False):
    class Tab(module.FlowMixin):
        pass

    tab = Tab()
    rng = random.Random(n)
    tab.times_sec, tab.weights = [], []
    t, mass = 0.0, 100.0
    for i in range(n):
        t += float(interval) * (1 + 0.02 * rng.random())  # readings never arrive exactly on time
        mass += 0.016 * float(interval) * (1 + 0.3 * math.sin(i / 7)) + rng.gauss(0, 0.002)
        tab.times_sec.append(t)
        tab.weights.append(mass)
    tab.flow_rates = [float(i) for i in range(n)] if stale else []  # values left by an earlier filter
    tab.ent_savgol_win, tab.ent_savgol_poly = _Box(savgol[0]), _Box(savgol[1])
    tab.combo_filter, tab.ent_filter_param = _Box(filt), _Box(param)
    tab.ent_interval, tab.ent_rpm, tab.ent_rollers = _Box(interval), _Box(rpm), _Box(rollers)
    return tab


CASES = [
    ("Mean", "60"),
    ("Mean", "120"),
    ("Mean", "1"),
    ("Mean", "not a number"),
    ("Median", "7"),
    ("Median", "120"),
    ("EMA", "0.1"),
    ("EMA", "1"),
    ("Butterworth", "0.05"),
    ("Butterworth", "5"),
    ("Adaptive", ""),
]


@pytest.mark.parametrize("n", [0, 1, 2, 4, 5, 61, 500])
@pytest.mark.parametrize(("filt", "param"), CASES)
@pytest.mark.parametrize("savgol", [("5", "3"), ("120", "1"), ("bad", "1")])
def test_same_numbers_as_before(n, filt, param, savgol):
    for stale in (False, True):
        old = _tab(flow_reference, n, filt, param, savgol, stale=stale)
        new = _tab(flow, n, filt, param, savgol, stale=stale)
        _assert_same(old, new)


def _assert_same(old, new):
    old.calculate_flows()
    new.calculate_flows()
    assert len(new.flow_rates) == len(old.flow_rates)
    for a, b in zip(old.flow_rates, new.flow_rates, strict=True):
        if a is None:
            assert b is None
        else:
            assert b == pytest.approx(float(a), rel=1e-12, abs=1e-12)


def test_adaptive_window_settings():
    for rpm, rollers, interval in (("5", "2", "3"), ("0", "x", "0.5")):
        old = _tab(flow_reference, 300, "Adaptive", "", rpm=rpm, rollers=rollers, interval=interval)
        new = _tab(flow, 300, "Adaptive", "", rpm=rpm, rollers=rollers, interval=interval)
        _assert_same(old, new)


@pytest.mark.parametrize("filt", ["Mean", "Median", "EMA", "Butterworth"])
def test_a_day_of_readings_stays_fast(filt):
    """8 hours of 1 s readings with a 120-point window used to take 1.7 s per new reading (Mean)."""
    tab = _tab(flow, 28_800, filt, "120" if filt in ("Mean", "Median") else "0.1", ("120", "1"))
    start = time.perf_counter()
    tab.calculate_flows()
    assert time.perf_counter() - start < 1.0  # about 0.01-0.08 s; generous for slow CI machines
