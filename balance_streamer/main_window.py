"""The main window: one Settings tab plus a tab per balance."""

import json
import logging
import os
import sys

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

from .balance_tab import BalanceTab
from .paths import CONFIG_DIR
from .settings_tab import SettingsTab
from .theme import apply_theme
from .update_panel import VersionStatus

log = logging.getLogger(__name__)


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

        if "app_geometry" in self.config:
            from PyQt6.QtCore import QByteArray

            self.restoreGeometry(QByteArray.fromHex(self.config["app_geometry"].encode()))

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

    def restart_app(self):
        self.save_config()
        for tab in self.tab_objects:
            if hasattr(tab, "save_tab_settings"):
                tab.save_tab_settings()
            if tab.serial_thread:
                tab.disconnect_serial()

        import subprocess

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
            os.replace(tmp_path, self.config_path)
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
        self.config["app_geometry"] = self.saveGeometry().toHex().data().decode()
        for tab in self.tab_objects:
            if hasattr(tab, "save_tab_settings"):
                tab.save_tab_settings()
            if tab.serial_thread:
                tab.disconnect_serial()
            tab.update_timer.stop()
        self.save_config()
        event.accept()
