"""The balance parsers turn one line from the serial port into (status, value, unit)."""

import pytest


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("  12.345 g\r\n", ("S", 12.345, "g")),
        ("-3.2 g", ("S", -3.2, "g")),
        ("150", ("S", 150.0, "g")),  # no unit sent: grams assumed
        ("", (None, None, None)),
    ],
)
def test_bonvoisin(mbs, line, expected):
    assert mbs.parse_bonvoisin_response(line) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("S S     100.123 g\r\n", ("S", 100.123, "g")),  # stable reading
        ("S D      -0.050 g", ("D", -0.05, "g")),  # dynamic (still settling)
        ("ES", (None, None, None)),  # MT-SICS syntax error reply
    ],
)
def test_mettler_toledo_mt_sics(mbs, line, expected):
    assert mbs.parse_mt_sics_response(line) == expected


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("     25.678 g\r\n", ("S", 25.678, "g")),
        ("-  1.20 g", ("S", -1.2, "g")),
        ("no reading", (None, None, None)),
    ],
)
def test_ohaus(mbs, line, expected):
    assert mbs.parse_ohaus_response(line) == expected
