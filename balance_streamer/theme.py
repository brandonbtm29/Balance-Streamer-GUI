"""Dark and light themes built from Qt's own Fusion style.

This replaces the pyqtdarktheme package, whose last release that installs on
Python 3.12+ dates from 2022. The colours follow that package's look so the app
looks much the same as before.
"""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

COLORS = {
    "dark": {
        "window": "#202124",
        "text": "#e4e7eb",
        "input": "#292a2d",
        "control": "#3f4042",
        "border": "#3f4042",
        "indicator": "#80868b",
        "accent": "#8ab4f8",
        "on_accent": "#202124",
        "hover": "#1e2b3c",
        "tab_selected": "#2e465e",
        "disabled": "#6b6e72",
        "link": "#8ab4f8",
    },
    "light": {
        "window": "#f8f9fa",
        "text": "#4d5157",
        "input": "#ffffff",
        "control": "#e8eaed",
        "border": "#dadce0",
        "indicator": "#80868b",
        "accent": "#0081db",
        "on_accent": "#f8f9fa",
        "hover": "#e8f0fe",
        "tab_selected": "#d2e3fc",
        "disabled": "#babdc2",
        "link": "#0081db",
    },
}


def palette(name):
    c = {k: QColor(v) for k, v in COLORS[name].items()}
    p = QPalette()
    roles = {
        QPalette.ColorRole.Window: c["window"],
        QPalette.ColorRole.WindowText: c["text"],
        QPalette.ColorRole.Base: c["input"],
        QPalette.ColorRole.AlternateBase: c["control"],
        QPalette.ColorRole.Text: c["text"],
        QPalette.ColorRole.Button: c["control"],
        QPalette.ColorRole.ButtonText: c["text"],
        QPalette.ColorRole.ToolTipBase: c["input"],
        QPalette.ColorRole.ToolTipText: c["text"],
        QPalette.ColorRole.PlaceholderText: c["disabled"],
        QPalette.ColorRole.Highlight: c["accent"],
        QPalette.ColorRole.HighlightedText: c["on_accent"],
        QPalette.ColorRole.Link: c["link"],
        QPalette.ColorRole.Mid: c["border"],
        QPalette.ColorRole.Midlight: c["control"],
        QPalette.ColorRole.Dark: c["border"],
        QPalette.ColorRole.Shadow: c["window"],
        QPalette.ColorRole.BrightText: c["accent"],
    }
    for role, color in roles.items():
        p.setColor(role, color)
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText):
        p.setColor(QPalette.ColorGroup.Disabled, role, c["disabled"])
    return p


def stylesheet(name):
    c = COLORS[name]
    return f"""
QPushButton {{
    border: 1px solid {c["border"]};
    border-radius: 4px;
    padding: 4px 8px;
    color: {c["accent"]};
    background-color: transparent;
}}
QPushButton:hover {{ background-color: {c["hover"]}; }}
QPushButton:disabled {{ color: {c["disabled"]}; }}
QLineEdit, QTextEdit, QPlainTextEdit {{
    border: 1px solid {c["border"]};
    border-radius: 4px;
    padding: 2px 4px;
}}
QLineEdit:focus, QTextEdit:focus {{ border-color: {c["accent"]}; }}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 13px;
    height: 13px;
    border: 1px solid {c["indicator"]};
    background-color: {c["input"]};
}}
QCheckBox::indicator {{ border-radius: 3px; }}
QRadioButton::indicator {{ border-radius: 7px; }}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {c["accent"]};
    border-color: {c["accent"]};
}}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{ border-color: {c["border"]}; }}
QTabBar::tab:selected {{ color: {c["accent"]}; background-color: {c["tab_selected"]}; }}
QGroupBox {{
    font-weight: bold;
    border: 1px solid {c["border"]};
    border-radius: 4px;
    margin-top: 9px;
    padding-top: 6px;
}}
QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 3px; }}
QToolTip {{ border: 1px solid {c["border"]}; }}
"""


def apply_theme(dark=True, app=None):
    """Switch the whole app to the dark or light theme."""
    app = app or QApplication.instance()
    name = "dark" if dark else "light"
    app.setStyle("Fusion")
    app.setPalette(palette(name))
    app.setStyleSheet(stylesheet(name))
