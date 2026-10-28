"""The main window: one Settings tab plus a tab per balance."""

import json
import logging
import os
import sys
import time

from PyQt6 import sip
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMessageBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import single_instance

from .balance_tab import BalanceTab
from .paths import APP_DIR, CONFIG_DIR
from .settings_tab import SettingsTab
from .theme import apply_theme
from .update_panel import VersionStatus

log = logging.getLogger(__name__)

# The window's size and position and each balance tab's dividers, kept per computer in the app
# folder (gitignored, like local_state.json). Not in config.json: that may be in a settings
# folder SyncThing shares between computers, and a Mac's layout doesn't fit the Windows PC.
WINDOW_STATE_FILE = "window_state.json"
WINDOW_STATE_PATH = os.path.join(APP_DIR, WINDOW_STATE_FILE)


def load_window_state():
    """The saved window layout for this computer ({} if there is none or it can't be read)."""
    try:
        with open(WINDOW_STATE_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    except (OSError, ValueError):
        log.warning("Couldn't read %s; using the default window layout", WINDOW_STATE_PATH, exc_info=True)
        return {}
    return data if isinstance(data, dict) else {}


def replace_file(src, dst, attempts=10, wait=0.1):
    """os.replace, retried briefly when Windows says "Access is denied".

    On Windows a file that SyncThing, antivirus or the search indexer has open for a moment can't
    be replaced, and os.replace raises PermissionError (WinError 5). That's always short-lived,
    so try again for about a second before giving up.
    """
    for attempt in range(attempts):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(wait)


def save_window_state(state):
    """Write the window layout safely: a crash mid-write leaves the old file, not half a file."""
    tmp_path = WINDOW_STATE_PATH + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        replace_file(tmp_path, WINDOW_STATE_PATH)
    except (OSError, TypeError, ValueError):
        log.warning("Couldn't save the window size and position to %s", WINDOW_STATE_PATH, exc_info=True)


class MultiBalanceApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Balance Data Streamer (PyQt6)")
        self.resize(1400, 800)

        self.config_path = os.path.join(CONFIG_DIR, "config.json")
        self.config = {"auto_connect": True, "known_balances": {}, "saved_tabs": []}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path) as f:
                    self.config.update(json.load(f))
            except (OSError, ValueError):
                # Keep the unreadable file so saving the defaults doesn't destroy it.
                log.exception("Couldn't read %s; starting from default settings", self.config_path)
                try:
                    os.replace(self.config_path, self.config_path + ".unreadable")
                    log.warning("Moved it to %s.unreadable", self.config_path)
                except OSError:
                    log.exception("Couldn't move %s aside", self.config_path)
        self._window_state = load_window_state()  # read before the tabs, which restore their dividers

        # Main Layout
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        layout.addWidget(self.tabs)

        self.tab_objects = []

        has_known = False
        if self.config.get("auto_connect", True):
            for name, details in self.config["known_balances"].items():
                self.add_tab_with_settings(name, details["brand"], details["port"])
                has_known = True

        if not has_known:
            self.add_tab()

        settings_tab = SettingsTab(self)
        self.settings_tab = settings_tab
        self.tabs.insertTab(0, settings_tab, "Settings")
        self.tabs.setCurrentIndex(1)  # Default to showing the first balance tab instead of settings

        # Bottom-right corner: the version, and a warning when a newer release is out.
        self.version_status = VersionStatus()
        self.statusBar().addPermanentWidget(self.version_status)
        settings_tab.update_panel.checked.connect(self.version_status.show_result)
        self.version_status.update_clicked.connect(self.show_update)

        # Size and position from last time on this computer (Qt keeps the window on a screen that
        # is still there). Older versions kept them in config.json as "app_geometry": that is used
        # until this computer has saved its own, and left in config.json for those versions.
        geometry = self._window_state.get("geometry")
        if not isinstance(geometry, str):
            geometry = self.config.get("app_geometry")
        if isinstance(geometry, str) and geometry:
            from PyQt6.QtCore import QByteArray

            self.restoreGeometry(QByteArray.fromHex(geometry.encode()))

    # --- window layout, remembered per computer (window_state.json in the app folder) -----------

    def tab_layout(self, tab_name):
        """The dividers saved on this computer for the balance tab with this name ({} if none)."""
        tabs = self._window_state.get("tabs")
        layout = tabs.get(tab_name) if isinstance(tabs, dict) else None
        return layout if isinstance(layout, dict) else {}

    def remember_window_state(self):
        """Save the window's size and position and each tab's dividers, for this computer only."""
        known = self.config.get("known_balances", {})
        saved_tabs = self._window_state.get("tabs")
        tabs = {}
        if isinstance(saved_tabs, dict):  # balances that are set up but not open right now
            tabs = {name: layout for name, layout in saved_tabs.items() if name in known}
        for tab in self.tab_objects:
            tabs[tab.tab_name] = tab.layout_state()
        self._window_state = {"geometry": self.saveGeometry().toHex().data().decode(), "tabs": tabs}
        save_window_state(self._window_state)

    # --- after the window is shown ----------------------------------------------------------

    def start_background_tasks(self):
        """Things that may take a moment, run once the window is up (not during tests)."""
        if self.settings_tab.update_panel.check_on_start():
            QTimer.singleShot(1500, lambda: self.settings_tab.update_panel.check(quiet=True))
        QTimer.singleShot(800, self.settings_tab.shortcut_panel.startup_check)

    def show_update(self):
        """Open Settings → Application Settings and show the update offer."""
        self.tabs.setCurrentWidget(self.settings_tab)
        self.settings_tab.sidebar.setCurrentRow(0)
        self.settings_tab.update_panel.offer_latest()

    def toggle_button_text(self, checked):
        self.config["show_button_text"] = checked
        self.save_config()
        for tab in self.tab_objects:
            if hasattr(tab, "update_button_text"):
                tab.update_button_text()

    def toggle_theme(self, checked=None):
        if checked is not None:
            self.config["dark_mode"] = checked
        else:
            self.config["dark_mode"] = self.action_dark_mode.isChecked()
        self.save_config()
        self.apply_theme()

    def apply_theme(self):
        apply_theme(dark=self.config.get("dark_mode", True))

    def show_help_dialog(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("About Flow Rate Engine")
        msg.setText(
            "<b>Derivative Engine:</b><br>"
            "This application uses a Savitzky-Golay (SavGol) filter to compute the flow rate (derivative) from the raw mass data. "
            "Savitzky-Golay fits a local polynomial to the data points, which smooths out high-frequency noise while calculating a highly accurate derivative.<br><br>"
            "<b>Secondary Smoothing:</b><br>"
            "Because flow rate is a derivative, it can be inherently noisy. Secondary Smoothing applies a final low-pass filter to the calculated flow rate for better visualization.<br>"
            "<ul>"
            "<li><b>Mean/Median:</b> Standard moving window averages.</li>"
            "<li><b>EMA:</b> Exponential Moving Average, gives more weight to recent data.</li>"
            "<li><b>Butterworth:</b> A sophisticated signal processing filter for extremely smooth lines.</li>"
            "<li><b>Adaptive:</b> Automatically adjusts its window size based on your pump RPM and roller count.</li>"
            "</ul>"
        )
        msg.exec()

    def recording_warning(self):
        """Ask-first text for anything that restarts the app: which tabs are recording ("" if none)."""
        recording = [t.tab_name for t in self.tab_objects if getattr(t, "recording", False)]
        if not recording:
            return ""
        return (
            "\n\nRecording is running in: " + ", ".join(recording) + ". It will stop; the data so far is "
            "kept in the backup file and can be brought back with Recover Session."
        )

    def restart_app(self):
        """Save everything, let go of the balances and start a new copy of the app."""
        self.remember_window_state()
        self.save_config()
        for tab in self.tab_objects:
            if hasattr(tab, "save_tab_settings"):
                tab.save_tab_settings()
            if tab.serial_thread:
                tab.disconnect_serial()

        import subprocess

        single_instance.release()  # or the new copy would find this one running and quit
        subprocess.Popen([sys.executable] + sys.argv)  # noqa: S603 (restarts this app)
        QApplication.quit()

    def save_config(self):
        if "known_balances" in self.config:
            new_known = {}
            for i in range(self.tabs.count()):
                tab = self.tabs.widget(i)
                if tab.tab_name in self.config["known_balances"]:
                    new_known[tab.tab_name] = self.config["known_balances"][tab.tab_name]
            for name, details in self.config["known_balances"].items():
                if name not in new_known:
                    new_known[name] = details
            self.config["known_balances"] = new_known

        try:
            tmp_path = self.config_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            replace_file(tmp_path, self.config_path)
        except (OSError, TypeError, ValueError):
            log.exception("Couldn't save settings to %s", self.config_path)

    def save_connection(self, name, brand, port):
        if "known_balances" not in self.config:
            self.config["known_balances"] = {}
        self.config["known_balances"][name] = {"brand": brand, "port": port, "unsaved": False}
        self.save_config()

    def set_unsaved_state(self, name, state):
        if "known_balances" in self.config and name in self.config["known_balances"]:
            self.config["known_balances"][name]["unsaved"] = state
            self.save_config()

    def add_tab(self, name=None):
        if not name:
            name = f"Balance {self.tabs.count() + 1}"
        self.add_tab_with_settings(name, "Bonvoisin", "")

    def add_tab_with_settings(self, name, brand, port):
        existing_names = [t.tab_name for t in self.tab_objects if hasattr(t, "tab_name")]
        unique_name = name
        counter = 1
        while unique_name in existing_names:
            unique_name = f"{name} ({counter})"
            counter += 1

        if name in self.config.get("known_balances", {}) and unique_name != name:
            self.config.setdefault("known_balances", {})[unique_name] = self.config["known_balances"][name]

        tab = BalanceTab(app=self, tab_name=unique_name)
        tab.combo_brand.setCurrentText(brand)
        if port:
            tab.combo_com.setCurrentText(port)

        tab.load_tab_settings()

        self.tabs.addTab(tab, unique_name)
        self.tab_objects.append(tab)
        self.tabs.setCurrentWidget(tab)

        if self.config.get("auto_connect", True) and port:
            # Skip it if the tab was closed in the meantime.
            QTimer.singleShot(500, lambda: None if sip.isdeleted(tab) else tab.connect_serial(auto=True))

    def rename_tab(self):
        widget = self.tabs.currentWidget()
        if not isinstance(widget, BalanceTab):
            return
        tab = widget
        idx = self.tabs.currentIndex()
        from PyQt6.QtWidgets import QInputDialog

        new_name, ok = QInputDialog.getText(self, "Rename Tab", "New Name:", text=tab.tab_name)
        if ok and new_name and new_name != tab.tab_name:
            if new_name in [t.tab_name for t in self.tab_objects]:
                return
            old_name = tab.tab_name
            tab.tab_name = new_name
            self.tabs.setTabText(idx, new_name)
            tab.ax_mass.set_title(f"{new_name} - Live Weight Data")
            tab.canvas.draw_idle()

            old_backup = tab.backup_path
            tab.setup_backup_path()
            if os.path.exists(old_backup):
                try:
                    os.rename(old_backup, tab.backup_path)
                except OSError:
                    log.warning("Couldn't rename backup %s to %s", old_backup, tab.backup_path, exc_info=True)

            if old_name in self.config.get("known_balances", {}):
                self.config["known_balances"][new_name] = self.config["known_balances"].pop(old_name)
                self.save_config()

    def close_tab(self, tab):
        idx = self.tabs.indexOf(tab)
        if idx >= 0:
            if hasattr(tab, "save_tab_settings"):
                tab.save_tab_settings()
            if tab.serial_thread:
                tab.disconnect_serial()
            tab.update_timer.stop()
            self.tabs.removeTab(idx)
            self.tab_objects.remove(tab)
            if tab.tab_name in self.config.get("known_balances", {}):
                del self.config["known_balances"][tab.tab_name]
                self.save_config()
            tab.deleteLater()

    def closeEvent(self, event):
        self.remember_window_state()
        for tab in self.tab_objects:
            if hasattr(tab, "save_tab_settings"):
                tab.save_tab_settings()
            if tab.serial_thread:
                tab.disconnect_serial()
            tab.update_timer.stop()
        self.save_config()
        event.accept()
