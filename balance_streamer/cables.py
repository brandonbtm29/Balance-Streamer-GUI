"""Recognise a balance's USB-to-serial cable, so the tab finds it again on another port.

Most USB-to-serial cables report a serial number of their own (FTDI and Silicon Labs chips do;
CH340 and Prolific ones often don't). When a tab connects, the cable on that port is remembered in
the shared settings, so the balance is found again after its cable moves to another USB socket,
its COM number changes, or the cable moves to another computer.

Without a serial number there's nothing to recognise, and the tab keeps using its saved port. Some
cheap copies all report the same serial number, so a cable is only used when exactly one port has
it and no other balance remembers the same one.
"""


def cable_of(info):
    """The cable on a port, from pyserial's port info: a dict, or None if it has no serial number."""
    serial_number = getattr(info, "serial_number", None)
    if not isinstance(serial_number, str) or not serial_number.strip():
        return None
    cable = {"serial_number": serial_number.strip()}
    for key in ("vid", "pid"):
        value = getattr(info, key, None)
        if isinstance(value, int):
            cable[key] = value
    for key in ("manufacturer", "description"):  # only to help people reading the settings file
        value = getattr(info, key, None)
        if isinstance(value, str) and value.strip() and value.strip().lower() != "n/a":
            cable[key] = value.strip()
    return cable


def same_cable(a, b):
    """Same serial number (and USB vendor and product IDs, where both are known)."""
    if not isinstance(a, dict) or not isinstance(b, dict) or not a.get("serial_number"):
        return False
    if a.get("serial_number") != b.get("serial_number"):
        return False
    return all(a[key] == b[key] for key in ("vid", "pid") if key in a and key in b)


def port_with_cable(cable, details):
    """The one port that has this cable now, or None (not plugged in, or on more than one port)."""
    matches = [port for port, info in details.items() if same_cable(cable_of(info), cable)]
    return matches[0] if len(matches) == 1 else None


def holds_other_cable(port, cable, details):
    """True when ``port`` has a recognisable cable that isn't ``cable``."""
    found = cable_of(details.get(port))
    return found is not None and not same_cable(found, cable)


def usable_cable(name, known_balances):
    """The cable remembered for the balance ``name``, unless another balance remembers the same one."""
    entry = known_balances.get(name)
    cable = entry.get("cable") if isinstance(entry, dict) else None
    if not isinstance(cable, dict) or not cable.get("serial_number"):
        return None
    for other, details in known_balances.items():
        if other != name and isinstance(details, dict) and same_cable(details.get("cable"), cable):
            return None
    return cable
