"""Saving and loading a tab's settings, in the app config and as named configurations."""

import datetime

from PyQt6.QtCore import QByteArray
from PyQt6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

# The tab's dividers: saved per computer in window_state.json (see main_window.py). Older
# versions kept them in config.json under the same names.
SPLITTERS = {"splitter_state": "splitter", "mid_splitter_state": "mid_splitter"}


class TabConfigMixin:
    """Part of BalanceTab: saving and loading a tab's settings, in the app config and as named configurations."""

    def layout_state(self):
        """This tab's dividers, for window_state.json."""
        return {
            key: getattr(self, attr).saveState().toHex().data().decode() for key, attr in SPLITTERS.items()
        }

    def restore_layout(self, layout):
        for key, attr in SPLITTERS.items():
            if isinstance(layout.get(key), str):
                getattr(self, attr).restoreState(QByteArray.fromHex(layout[key].encode()))

    def save_tab_settings(self):
        if not self.app:
            return
        kb = self.app.config.get("known_balances", {})
        if self.tab_name not in kb:
            kb[self.tab_name] = {
                "brand": self.combo_brand.currentText(),
                "port": self.combo_com.currentText(),
                "unsaved": False,
            }
        old = kb[self.tab_name].get("settings") or {}
        kb[self.tab_name]["settings"] = {
            "interval": self.ent_interval.text(),
            "savgol_win": self.ent_savgol_win.text(),
            "savgol_poly": self.ent_savgol_poly.text(),
            "filter_type": self.combo_filter.currentText(),
            "filter_param": self.ent_filter_param.text(),
            "rpm": self.ent_rpm.text(),
            "rollers": self.ent_rollers.text(),
            "do_auto_scale_x": self.chk_auto_x.isChecked(),
            "do_auto_scale_y_mass": self.chk_auto_y_mass.isChecked(),
            "do_auto_scale_y_flow": self.chk_auto_y_flow.isChecked(),
            "do_auto_stop": self.chk_auto_stop.isChecked(),
            "auto_stop_min": self.ent_auto_stop_min.text(),
            "auto_stop_thresh": self.ent_auto_stop_thresh.text(),
            "experiment_notes": self.txt_notes.toPlainText(),
            "save_folder": self.ent_save_folder.toPlainText().replace("\n", "").strip(),
            "use_global_template": self.chk_use_global_template.isChecked(),
            "save_template": self.ent_save_template.text(),
            "autosave_mode": self.combo_autosave.currentText(),
            "autosave_min": self.ent_autosave_min.text(),
            "save_on_pause": self.chk_save_on_pause.isChecked(),
            "xmin": self.ent_xmin.text(),
            "xmax": self.ent_xmax.text(),
            "ymin": self.ent_ymin.text(),
            "ymax": self.ent_ymax.text(),
            "flowmin": self.ent_flowmin.text(),
            "flowmax": self.ent_flowmax.text(),
            "col_widths": [self.table.columnWidth(i) for i in range(self.table.columnCount())],
        }
        # The dividers are now saved per computer; keep any old values for older versions.
        for key in SPLITTERS:
            if key in old:
                kb[self.tab_name]["settings"][key] = old[key]

        if hasattr(self, "token_inputs"):
            kb[self.tab_name]["settings"]["tab_tokens"] = {k: v.text() for k, v in self.token_inputs.items()}

    def load_tab_settings(self):
        if not self.app:
            return
        kb = self.app.config.get("known_balances", {})
        # Dividers: this computer's own, or else the ones an older version saved in config.json.
        old = kb.get(self.tab_name, {}).get("settings") or {}
        self.restore_layout(self.app.tab_layout(self.tab_name) or old)
        if self.tab_name in kb and "settings" in kb[self.tab_name]:
            settings = kb[self.tab_name]["settings"]
            if "interval" in settings:
                self.ent_interval.setText(settings["interval"])
            if "savgol_win" in settings:
                self.ent_savgol_win.setText(settings["savgol_win"])
            if "savgol_poly" in settings:
                self.ent_savgol_poly.setText(settings["savgol_poly"])
            if "filter_type" in settings:
                self.combo_filter.setCurrentText(settings["filter_type"])
            if "filter_param" in settings:
                self.ent_filter_param.setText(settings["filter_param"])
            if "rpm" in settings:
                self.ent_rpm.setText(settings["rpm"])
            if "rollers" in settings:
                self.ent_rollers.setText(settings["rollers"])
            if "do_auto_scale_x" in settings:
                self.chk_auto_x.setChecked(settings["do_auto_scale_x"])
            if "do_auto_scale_y_mass" in settings:
                self.chk_auto_y_mass.setChecked(settings["do_auto_scale_y_mass"])
            if "do_auto_scale_y_flow" in settings:
                self.chk_auto_y_flow.setChecked(settings["do_auto_scale_y_flow"])
            if "do_auto_stop" in settings:
                self.chk_auto_stop.setChecked(settings["do_auto_stop"])
            if "auto_stop_min" in settings:
                self.ent_auto_stop_min.setText(settings["auto_stop_min"])
            if "auto_stop_thresh" in settings:
                self.ent_auto_stop_thresh.setText(settings["auto_stop_thresh"])
            if "experiment_notes" in settings:
                self.txt_notes.setText(settings["experiment_notes"])
            if "save_folder" in settings:
                self.ent_save_folder.setPlainText(settings["save_folder"])

            if "xmin" in settings:
                self.ent_xmin.setText(settings["xmin"])
            if "xmax" in settings:
                self.ent_xmax.setText(settings["xmax"])
            if "ymin" in settings:
                self.ent_ymin.setText(settings["ymin"])
            if "ymax" in settings:
                self.ent_ymax.setText(settings["ymax"])
            if "flowmin" in settings:
                self.ent_flowmin.setText(settings["flowmin"])
            if "flowmax" in settings:
                self.ent_flowmax.setText(settings["flowmax"])

            if "use_global_template" in settings:
                self.chk_use_global_template.setChecked(settings["use_global_template"])
            if "save_template" in settings:
                self.ent_save_template.setText(settings["save_template"])

            if "autosave_mode" in settings:
                self.combo_autosave.setCurrentText(settings["autosave_mode"])
            if "autosave_min" in settings:
                self.ent_autosave_min.setText(settings["autosave_min"])
            if "save_on_pause" in settings:
                self.chk_save_on_pause.setChecked(settings["save_on_pause"])

            if "col_widths" in settings:
                for i, w in enumerate(settings["col_widths"]):
                    if i < self.table.columnCount():
                        self.table.setColumnWidth(i, w)

            if "tab_tokens" in settings and hasattr(self, "token_inputs"):
                for name, val in settings["tab_tokens"].items():
                    if name in self.token_inputs:
                        self.token_inputs[name].setText(val)
                    else:
                        self.add_custom_token_ui(name, val)

    def save_tab_config(self):
        settings_dict = {
            "interval": self.ent_interval.text(),
            "savgol_win": self.ent_savgol_win.text(),
            "savgol_poly": self.ent_savgol_poly.text(),
            "filter_type": self.combo_filter.currentText(),
            "filter_param": self.ent_filter_param.text(),
            "rpm": self.ent_rpm.text(),
            "rollers": self.ent_rollers.text(),
            "do_auto_scale_x": self.chk_auto_x.isChecked(),
            "do_auto_scale_y_mass": self.chk_auto_y_mass.isChecked(),
            "do_auto_scale_y_flow": self.chk_auto_y_flow.isChecked(),
            "do_auto_stop": self.chk_auto_stop.isChecked(),
            "auto_stop_min": self.ent_auto_stop_min.text(),
            "auto_stop_thresh": self.ent_auto_stop_thresh.text(),
            "experiment_notes": self.txt_notes.toPlainText(),
            "save_folder": self.ent_save_folder.toPlainText().replace("\n", "").strip(),
            "use_global_template": self.chk_use_global_template.isChecked(),
            "save_template": self.ent_save_template.text(),
            "autosave_mode": self.combo_autosave.currentText(),
            "autosave_min": self.ent_autosave_min.text(),
            "save_on_pause": self.chk_save_on_pause.isChecked(),
            "xmin": self.ent_xmin.text(),
            "xmax": self.ent_xmax.text(),
            "ymin": self.ent_ymin.text(),
            "ymax": self.ent_ymax.text(),
            "flowmin": self.ent_flowmin.text(),
            "flowmax": self.ent_flowmax.text(),
        }

        if hasattr(self, "token_inputs"):
            settings_dict["tab_tokens"] = {k: v.text() for k, v in self.token_inputs.items()}

        cfg = {
            "name": self.tab_name,
            "brand": self.combo_brand.currentText(),
            "port": self.combo_com.currentText(),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "settings": settings_dict,
        }
        saved = self.app.config.setdefault("saved_tabs", [])
        found = False
        for i, s in enumerate(saved):
            if s.get("name") == self.tab_name:
                saved[i] = cfg
                found = True
                break
        if not found:
            saved.append(cfg)

        self.app.save_config()
        QMessageBox.information(self, "Success", "Tab Configuration Saved.")

    def load_tab_config_dialog(self):
        saved_tabs = self.app.config.get("saved_tabs", [])
        if not saved_tabs:
            QMessageBox.information(self, "Info", "No saved tab configurations found.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Load Tab Configuration")
        dialog.setMinimumSize(400, 300)
        layout = QVBoxLayout(dialog)
        layout.addWidget(QLabel("Select a saved tab configuration to load as a new tab:"))

        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        bg = QButtonGroup(dialog)

        for i, cfg in enumerate(saved_tabs):
            text = f"{cfg.get('name', 'Unknown')} - {cfg.get('brand', '')} on {cfg.get('port', '')} ({cfg.get('timestamp', '')})"
            rb = QRadioButton(text)
            if i == 0:
                rb.setChecked(True)
            bg.addButton(rb, i)
            scroll_layout.addWidget(rb)

        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        layout.addWidget(scroll)

        btn_layout = QHBoxLayout()
        btn_load = QPushButton("Load Selected")
        btn_delete = QPushButton("Delete Selected")
        btn_delete.setStyleSheet("background-color: #e74c3c; color: white;")
        btn_cancel = QPushButton("Cancel")

        btn_layout.addWidget(btn_load)
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)

        def do_load():
            idx = bg.checkedId()
            if idx >= 0:
                cfg = saved_tabs[idx]
                cfg_name = cfg.get("name", "New Tab")
                brand = cfg.get("brand", "")
                port = cfg.get("port", "")
                settings = cfg.get("settings", {})

                kb = self.app.config.setdefault("known_balances", {})
                kb[cfg_name] = {"brand": brand, "port": port, "settings": settings, "unsaved": False}

                from .balance_tab import BalanceTab  # here to avoid a circular import

                current_tab = self.app.tabs.currentWidget() if self.app else None
                is_unused = False
                if isinstance(current_tab, BalanceTab):
                    is_unused = (
                        (not current_tab.times_sec)
                        and (not current_tab.recording)
                        and (not current_tab.serial_thread)
                    )

                if is_unused:
                    current_tab.tab_name = cfg_name
                    idx_tab = self.app.tabs.indexOf(current_tab)
                    if idx_tab >= 0:
                        self.app.tabs.setTabText(idx_tab, cfg_name)
                    current_tab.combo_brand.setCurrentText(brand)
                    if port:
                        current_tab.combo_com.setCurrentText(port)
                    current_tab.load_tab_settings()
                    current_tab.setup_backup_path()
                    current_tab.ax_mass.set_title(f"{cfg_name} - Live Weight Data")
                    current_tab.canvas.draw_idle()
                else:
                    self.app.add_tab_with_settings(cfg_name, brand, port)
            dialog.accept()

        def do_delete():
            idx = bg.checkedId()
            if idx >= 0:
                del saved_tabs[idx]
                self.app.save_config()
                dialog.accept()
                self.load_tab_config_dialog()

        btn_load.clicked.connect(do_load)
        btn_delete.clicked.connect(do_delete)
        btn_cancel.clicked.connect(dialog.reject)
        dialog.exec()
