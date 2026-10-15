"""Turn one line from a balance's serial port into (status, value, unit)."""

import re


def parse_bonvoisin_response(response_str):
    match = re.search(r"([-+]?(?:\d+\.\d+|\d+))", response_str)
    if match:
        value = float(match.group(1))
        unit_match = re.search(r"([a-zA-Z]+)", response_str)
        unit = unit_match.group(1) if unit_match else "g"
        return "S", value, unit
    return None, None, None


mt_response_pattern = re.compile(r"S\s+([SD])\s+([ \-0-9\.]+)\s+([a-zA-Z]+)")


def parse_mt_sics_response(response_str):
    match = mt_response_pattern.search(response_str)
    if match:
        status, value_str, unit = match.groups()
        value = float(value_str.replace(" ", ""))
        return status, value, unit
    return None, None, None


ohaus_response_pattern = re.compile(r"([+-]?\s*[\d\.]+)\s+([a-zA-Z]+)")


def parse_ohaus_response(response_str):
    match = ohaus_response_pattern.search(response_str)
    if match:
        val_str, unit = match.groups()
        value = float(val_str.replace(" ", ""))
        return "S", value, unit
    return None, None, None
