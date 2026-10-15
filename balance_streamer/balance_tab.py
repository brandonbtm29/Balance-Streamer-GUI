"""One balance tab. Flow maths, export, recovery and tab settings live in mixin modules."""

import csv
import datetime
import logging
import os
import time

import matplotlib
import serial
import serial.tools.list_ports
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
import scipy.signal
import scipy.stats
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from .export import ExportMixin
from .flow import FlowMixin
from .recovery import RecoveryMixin
from .serial_worker import SerialWorker
from .tab_config import TabConfigMixin
from .widgets import CollapsibleBox

log = logging.getLogger(__name__)


class BalanceTab(FlowMixin, ExportMixin, RecoveryMixin, TabConfigMixin, QWidget):
    """One tab per balance: connection, live chart, table, filters and saving."""

    def __init__(self, parent=None, app=None, tab_name="Balance"):
        super().__init__(parent)
        self.app = app
        self.tab_name = tab_name
        self.serial_thread = None

        # Data tracking
        self.times_sec = []
        self.times_min = []
        self.weights = []
        self.flow_rates = []
        self.timestamps = []
        self.start_time = None
        self.last_recorded_time = 0
        self.unsaved_changes = False

        self.recording = False
        self.current_unit = "g"
        self.unit_set = False

        # Backup path
        self.setup_backup_path()

        self.build_ui()
        self.load_tab_settings()

        # Update timer for GUI plotting
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_gui_components)
        self.update_timer.start(500)  # 2 Hz update

    def setup_backup_path(self):
        backup_dir = os.path.join(os.getcwd(), "Data Backups")
        os.makedirs(backup_dir, exist_ok=True)
        self.backup_path = os.path.join(backup_dir, f"{self.tab_name.replace(' ', '_')}_Backup.csv")
        self.prune_backup_file()

    def update_button_text(self):
        show_text = self.app.config.get("show_button_text", False) if self.app else False

        if self.recording:
            self.btn_record.setText("⏹ Stop Recording" if show_text else "⏹")
        else:
            self.btn_record.setText("▶ Start Recording" if show_text else "▶")

        self.btn_clear.setText("🗑 Clear Data" if show_text else "🗑")
        self.btn_save_excel.setText("📊 Save to Excel" if show_text else "📊")
        self.btn_tare.setText("⚖ Tare Balance" if show_text else "⚖")
        self.btn_save_graph.setText("🖼 Save Graph PNG" if show_text else "🖼")
        self.btn_quick_save.setText("⚡ Quick Save" if show_text else "⚡")
        self.btn_recover.setText("↺ Recover Session" if show_text else "↺")

    def build_ui(self):
        main_layout = QVBoxLayout(self)

        self.top_action_layout = QHBoxLayout()

        self.btn_record = QPushButton()
        self.btn_record.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
        self.btn_record.clicked.connect(self.toggle_record)
        self.btn_record.setToolTip("Start Recording")

        self.btn_clear = QPushButton()
        self.btn_clear.setStyleSheet("background-color: #e74c3c; color: white;")
        self.btn_clear.clicked.connect(self.clear_data)
        self.btn_clear.setToolTip("Clear Data")

        self.btn_save_excel = QPushButton()
        self.btn_save_excel.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_save_excel.clicked.connect(self.save_excel)
        self.btn_save_excel.setToolTip("Save to Excel")

        self.btn_tare = QPushButton()
        self.btn_tare.clicked.connect(self.tare_balance)
        self.btn_tare.setToolTip("Tare Balance")

        self.btn_save_graph = QPushButton()
        self.btn_save_graph.setStyleSheet("background-color: #2980b9; color: white;")
        self.btn_save_graph.clicked.connect(self.save_graph)
        self.btn_save_graph.setToolTip("Save Graph PNG")

        self.btn_quick_save = QPushButton()
        self.btn_quick_save.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        self.btn_quick_save.setToolTip("Instantly overwrite the target Auto-Save file without prompting.")
        self.btn_quick_save.clicked.connect(lambda checked=False: self.save_excel(quick_save=True))

        self.top_action_layout.addWidget(self.btn_record)
        self.top_action_layout.addWidget(self.btn_clear)
        self.top_action_layout.addWidget(self.btn_save_excel)
        self.top_action_layout.addWidget(self.btn_quick_save)
        self.top_action_layout.addWidget(self.btn_tare)
        self.top_action_layout.addWidget(self.btn_save_graph)
        self.btn_recover = QPushButton()
        self.btn_recover.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold;")
        self.btn_recover.clicked.connect(self.prompt_session_recovery)
        self.btn_recover.setToolTip("Recover Session")
        self.top_action_layout.addWidget(self.btn_recover)
        self.top_action_layout.addStretch()

        main_layout.addLayout(self.top_action_layout)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(self.splitter)

        self.update_button_text()

        # --- LEFT PANEL ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left_widget)

        def create_form_row(layout, label, default=""):
            row = QHBoxLayout()
            lbl = QLabel(label)
            ent = QLineEdit(default)
            row.addWidget(lbl)
            row.addWidget(ent)
            layout.addLayout(row)
            return ent

        self.left_panels = {}

        # Recording Settings
        gb_rec = CollapsibleBox("Recording Settings")
        l_rec = QVBoxLayout()
        gb_rec.setLayout(l_rec)
        self.ent_interval = create_form_row(l_rec, "Interval (s):", "1.0")

        self.chk_auto_stop = QCheckBox("Enable Auto-Stop")
        l_rec.addWidget(self.chk_auto_stop)
        self.ent_auto_stop_min = create_form_row(l_rec, "Auto-Stop After (min):", "5.0")
        self.ent_auto_stop_thresh = create_form_row(l_rec, "Flow Threshold:", "0.1")
        self.left_panels["Recording Settings"] = gb_rec

        # Derivative Engine
        gb_der = CollapsibleBox("Derivative Engine")
        l_der = QVBoxLayout()
        gb_der.setLayout(l_der)
        self.ent_savgol_win = create_form_row(l_der, "SavGol Window:", "5")
        self.ent_savgol_poly = create_form_row(l_der, "SavGol Poly:", "3")
        self.left_panels["Derivative Engine"] = gb_der

        # Filtering
        gb_filt = CollapsibleBox("Secondary Smoothing")
        l_filt = QVBoxLayout()
        gb_filt.setLayout(l_filt)
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["Mean", "Median", "EMA", "Butterworth", "Adaptive"])
        self.combo_filter.currentTextChanged.connect(self.on_filter_change)
        l_filt.addWidget(self.combo_filter)

        self.lbl_filter_param = QLabel("Window Size (samples):")
        l_filt.addWidget(self.lbl_filter_param)
        self.ent_filter_param = QLineEdit("20")
        l_filt.addWidget(self.ent_filter_param)

        self.btn_apply_filter = QPushButton("Apply Smoothing")
        self.btn_apply_filter.setStyleSheet("background-color: #27ae60; color: white;")
        self.btn_apply_filter.clicked.connect(self.manual_apply_filters)
        l_filt.addWidget(self.btn_apply_filter)

        self.left_panels["Secondary Smoothing"] = gb_filt

        # Calibration
        gb_cal = CollapsibleBox("Pump Calibration")
        gb_cal.set_collapsed(True)
        l_cal = QVBoxLayout()
        gb_cal.setLayout(l_cal)
        self.ent_rpm = create_form_row(l_cal, "Pump RPM:", "30")
        self.ent_rollers = create_form_row(l_cal, "Rollers:", "3")
        self.btn_log_cal = QPushButton("Log Calibration Point")
        self.btn_log_cal.setStyleSheet("background-color: #8e44ad; color: white; font-weight: bold;")
        self.btn_log_cal.clicked.connect(self.log_calibration)
        l_cal.addWidget(self.btn_log_cal)
        self.left_panels["Pump Calibration"] = gb_cal

        # Axis Limits
        gb_axis = CollapsibleBox("Axis Limits")
        gb_axis.set_collapsed(True)
        l_axis = QVBoxLayout()
        gb_axis.setLayout(l_axis)

        self.chk_auto_x = QCheckBox("Auto Time")
        self.chk_auto_x.setChecked(True)
        self.chk_auto_y_mass = QCheckBox("Auto Mass")
        self.chk_auto_y_mass.setChecked(True)
        self.chk_auto_y_flow = QCheckBox("Auto Flow")
        self.chk_auto_y_flow.setChecked(True)
        self.chk_show_flow = QCheckBox("Show Flow Rate")
        self.chk_show_flow.setChecked(True)
        self.chk_show_flow.stateChanged.connect(self.toggle_flow_axis)

        l_axis.addWidget(self.chk_auto_x)
        l_axis.addWidget(self.chk_auto_y_mass)
        l_axis.addWidget(self.chk_auto_y_flow)
        l_axis.addWidget(self.chk_show_flow)

        self.combo_xaxis = QComboBox()
        self.combo_xaxis.addItems(["Duration", "Timestamp"])
        l_axis.addWidget(QLabel("Plot X-Axis By:"))
        l_axis.addWidget(self.combo_xaxis)

        self.ent_xmin = create_form_row(l_axis, "X Min (min):", "0")
        self.ent_xmax = create_form_row(l_axis, "X Max (min):", "10")
        self.ent_ymin = create_form_row(l_axis, "Mass Min (g):", "0")
        self.ent_ymax = create_form_row(l_axis, "Mass Max (g):", "100")
        self.ent_flowmin = create_form_row(l_axis, "Flow Min:", "0")
        self.ent_flowmax = create_form_row(l_axis, "Flow Max:", "20")

        self.btn_apply_lims = QPushButton("Apply Manual Limits")
        self.btn_apply_lims.clicked.connect(self.apply_axis_limits)
        l_axis.addWidget(self.btn_apply_lims)
        self.left_panels["Axis Limits"] = gb_axis

        # Data Analysis
        gb_ana = CollapsibleBox("Data Analysis")
        l_ana = QVBoxLayout()
        gb_ana.setLayout(l_ana)
        self.ent_fit_start = create_form_row(l_ana, "Fit Start (min):", "0")
        self.ent_fit_end = create_form_row(l_ana, "Fit End (min):", "10")
        self.btn_apply_fit = QPushButton("Apply Linear Fit")
        self.btn_apply_fit.setStyleSheet("background-color: #e67e22; color: white;")
        self.btn_apply_fit.clicked.connect(self.apply_linear_fit)
        l_ana.addWidget(self.btn_apply_fit)
        self.left_panels["Data Analysis"] = gb_ana

        left_order = (
            self.app.config.get(
                "left_panel_order",
                [
                    "Recording Settings",
                    "Derivative Engine",
                    "Secondary Smoothing",
                    "Pump Calibration",
                    "Axis Limits",
                    "Data Analysis",
                ],
            )
            if self.app
            else [
                "Recording Settings",
                "Derivative Engine",
                "Secondary Smoothing",
                "Pump Calibration",
                "Axis Limits",
                "Data Analysis",
            ]
        )

        for name in left_order:
            if name in self.left_panels:
                left_layout.addWidget(self.left_panels[name])

        left_layout.addStretch()

        self.splitter.addWidget(left_scroll)

        # --- MIDDLE PANEL ---
        mid_widget = QWidget()
        mid_layout = QVBoxLayout(mid_widget)
        self.mid_splitter = QSplitter(Qt.Orientation.Vertical)
        mid_layout.addWidget(self.mid_splitter)

        # Plot
        self.fig, self.ax_mass = plt.subplots(figsize=(8, 6))
        self.fig.patch.set_facecolor("white")
        self.ax_mass.set_facecolor("white")
        self.ax_flow = self.ax_mass.twinx()

        self.ax_mass.set_title(f"{self.tab_name} - Live Weight Data", color="black")
        self.ax_mass.set_xlabel("Time (minutes)", color="black")
        self.ax_mass.set_ylabel("Weight (g)", color="#2980b9")
        self.ax_mass.tick_params(axis="x", colors="black")
        self.ax_mass.tick_params(axis="y", labelcolor="#2980b9")
        self.ax_mass.grid(True, alpha=0.3, color="gray")

        self.ax_flow.set_ylabel("Flow Rate (g/min)", color="#c0392b")
        self.ax_flow.tick_params(axis="y", labelcolor="#c0392b")

        (self.line_mass,) = self.ax_mass.plot(
            [], [], marker="o", linestyle="-", color="#3498db", label="Mass"
        )
        (self.line_flow,) = self.ax_flow.plot([], [], marker="", linestyle="-", color="#e74c3c", label="Flow")
        (self.line_fit,) = self.ax_mass.plot(
            [], [], marker="", linestyle="--", color="#f1c40f", label="Linear Fit", linewidth=2.5
        )
        self.fig.tight_layout()

        self.canvas = FigureCanvasQTAgg(self.fig)
        self.mid_splitter.addWidget(self.canvas)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Duration (min)", "Mass (g)", "Flow (g/min)"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.mid_splitter.addWidget(self.table)

        self.splitter.addWidget(mid_widget)

        # --- RIGHT PANEL ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_scroll = QScrollArea()
        right_scroll.setMinimumWidth(360)
        right_scroll.setWidgetResizable(True)
        right_scroll.setWidget(right_widget)

        # Tab Management
        gb_tab = CollapsibleBox("Tab Management")
        l_tab = QVBoxLayout()
        gb_tab.setLayout(l_tab)

        l_tab.addWidget(QLabel("New Tab Name:"))
        self.ent_new_tab = QLineEdit()
        l_tab.addWidget(self.ent_new_tab)

        btn_add_tab = QPushButton("Add Tab")
        btn_add_tab.clicked.connect(self.request_add_tab)
        l_tab.addWidget(btn_add_tab)

        btn_rename_tab = QPushButton("Rename Current Tab")
        btn_rename_tab.clicked.connect(self.request_rename_tab)
        l_tab.addWidget(btn_rename_tab)

        self.btn_save_tab = QPushButton("Save Tab Configuration")
        self.btn_save_tab.clicked.connect(self.save_tab_config)
        l_tab.addWidget(self.btn_save_tab)

        self.btn_load_tab = QPushButton("Load Tab Configuration")
        self.btn_load_tab.clicked.connect(self.load_tab_config_dialog)
        l_tab.addWidget(self.btn_load_tab)

        self.btn_close_tab = QPushButton("✖ Close Tab")
        self.btn_close_tab.setStyleSheet("background-color: #e74c3c; color: white;")
        self.btn_close_tab.clicked.connect(self.close_tab)
        l_tab.addWidget(self.btn_close_tab)

        right_layout.addWidget(gb_tab)

        # Connection
        gb_conn = CollapsibleBox("Connection")
        l_conn = QVBoxLayout()
        gb_conn.setLayout(l_conn)
        l_conn.addWidget(QLabel("Balance Brand:"))
        self.combo_brand = QComboBox()
        self.combo_brand.addItems(["Bonvoisin", "Mettler Toledo", "Ohaus Adventurer", "Lachoi"])
        l_conn.addWidget(self.combo_brand)

        l_conn.addWidget(QLabel("COM Port:"))
        self.combo_com = QComboBox()
        self.refresh_com_ports()
        l_conn.addWidget(self.combo_com)

        self.btn_refresh = QPushButton("Refresh Ports")
        self.btn_refresh.clicked.connect(self.refresh_com_ports)
        l_conn.addWidget(self.btn_refresh)

        self.btn_connect = QPushButton("Connect")
        self.btn_connect.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        self.btn_connect.clicked.connect(self.connect_serial)
        l_conn.addWidget(self.btn_connect)

        self.btn_disconnect = QPushButton("Disconnect")
        self.btn_disconnect.setStyleSheet("background-color: #e74c3c; color: white;")
        self.btn_disconnect.clicked.connect(self.disconnect_serial)
        l_conn.addWidget(self.btn_disconnect)

        self.lbl_status = QLabel("Status: Disconnected")
        self.lbl_status.setStyleSheet("color: gray; font-weight: bold;")
        l_conn.addWidget(self.lbl_status)
        right_layout.addWidget(gb_conn)

        # Save Settings
        gb_save = CollapsibleBox("Auto-Save Settings")
        l_save = QVBoxLayout()
        gb_save.setLayout(l_save)

        l_save.addWidget(QLabel("Save Folder Path:"))
        folder_layout = QVBoxLayout()
        default_folder = self.app.config.get("global_default_save_folder", "Data") if self.app else "Data"
        self.ent_save_folder = QTextEdit(default_folder)
        self.ent_save_folder.setFixedHeight(45)
        btn_browse = QPushButton("Browse")
        btn_browse.setMinimumHeight(35)
        btn_browse.clicked.connect(self.browse_save_folder)
        folder_layout.addWidget(self.ent_save_folder)
        folder_layout.addWidget(btn_browse)
        l_save.addLayout(folder_layout)

        l_save.addSpacing(10)

        # Template
        self.chk_use_global_template = QCheckBox("Use Global Filename Template")
        self.chk_use_global_template.setChecked(True)
        self.chk_use_global_template.stateChanged.connect(self.toggle_template_source)
        l_save.addWidget(self.chk_use_global_template)

        temp_layout = QHBoxLayout()
        temp_layout.addWidget(QLabel("Tab Template:"))
        self.ent_save_template = QLineEdit()
        if self.app:
            self.ent_save_template.setText(
                self.app.config.get("global_filename_template", "<Tab Name>_<Date>_<Time>")
            )
        self.ent_save_template.setEnabled(False)
        temp_layout.addWidget(self.ent_save_template)
        l_save.addLayout(temp_layout)

        self.local_token_grid = QGridLayout()
        self.refresh_local_token_buttons()
        l_save.addLayout(self.local_token_grid)

        l_save.addSpacing(10)

        mode_layout = QFormLayout()
        mode_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.combo_autosave = QComboBox()
        self.combo_autosave.addItems(["Off", "On Auto-Stop", "Every X Minutes"])
        mode_layout.addRow("Auto-Save Mode:", self.combo_autosave)

        self.ent_autosave_min = QLineEdit("5.0")
        mode_layout.addRow("Auto-Save Interval (min):", self.ent_autosave_min)
        l_save.addLayout(mode_layout)

        self.chk_save_on_pause = QCheckBox("Save Data Automatically on Pause")
        self.chk_save_on_pause.setChecked(False)
        l_save.addWidget(self.chk_save_on_pause)

        self.combo_autosave.currentIndexChanged.connect(self.toggle_autosave_interval)
        self.toggle_autosave_interval()

        right_layout.addWidget(gb_save)

        # Metadata Tokens
        self.gb_tokens = CollapsibleBox("Metadata Tokens")
        self.tokens_outer_layout = QVBoxLayout()
        self.gb_tokens.setLayout(self.tokens_outer_layout)
        self.l_tokens = QFormLayout()
        self.l_tokens.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.tokens_outer_layout.addLayout(self.l_tokens)

        self.btn_add_tab_token = QPushButton("+ Add Custom Token")
        self.btn_add_tab_token.clicked.connect(self.request_add_custom_token)
        self.tokens_outer_layout.addWidget(self.btn_add_tab_token)

        self.token_inputs = {}
        right_layout.addWidget(self.gb_tokens)
        self.refresh_tokens()

        # Notes
        gb_notes = CollapsibleBox("Experiment Notes")
        l_notes = QVBoxLayout()
        gb_notes.setLayout(l_notes)
        self.txt_notes = QTextEdit()
        self.txt_notes.setMinimumHeight(150)
        l_notes.addWidget(self.txt_notes)
        right_layout.addWidget(gb_notes)

        # btn_save_tab moved to Tab Management

        right_layout.addStretch()
        self.splitter.addWidget(right_scroll)

        self.splitter.setSizes([300, 600, 300])

    def refresh_local_token_buttons(self):
        while self.local_token_grid.count():
            item = self.local_token_grid.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        base_tokens = ["Tab Name", "Date", "Time", "Start Date", "Start Time"]
        all_tokens = base_tokens.copy()

        global_tokens = self.app.config.get("global_tokens", []) if self.app else []
        for t in global_tokens:
            n = t.get("name")
            if n and n not in all_tokens:
                all_tokens.append(n)

        for name in getattr(self, "token_inputs", {}):
            if name not in all_tokens:
                all_tokens.append(name)

        row = 0
        col = 0
        for tok in all_tokens:
            btn = QPushButton(f"<{tok}>")
            btn.clicked.connect(lambda checked, t=tok: self.ent_save_template.insert(f"<{t}>"))
            self.local_token_grid.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1

    def refresh_tokens(self):
        old_values = {k: v.text() for k, v in getattr(self, "token_inputs", {}).items()}

        while self.l_tokens.rowCount() > 0:
            self.l_tokens.removeRow(0)

        self.token_inputs = {}

        global_tokens = self.app.config.get("global_tokens", []) if self.app else []
        global_names = []
        for t in global_tokens:
            name = t.get("name", "").strip()
            if name:
                global_names.append(name)
                ent = QLineEdit()
                if name in old_values:
                    ent.setText(old_values[name])
                else:
                    ent.setText(t.get("value", ""))
                self.l_tokens.addRow(name + ":", ent)
                self.token_inputs[name] = ent

        for name, val in old_values.items():
            if name not in global_names:
                self.add_custom_token_ui(name, val)

        if hasattr(self, "refresh_local_token_buttons"):
            self.refresh_local_token_buttons()

    def request_add_custom_token(self):
        from PyQt6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "Add Custom Token", "Token Name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.token_inputs:
                QMessageBox.warning(self, "Warning", "Token already exists!")
                return
            self.add_custom_token_ui(name, "")

    def add_custom_token_ui(self, name, value):
        ent = QLineEdit(value)
        row_layout = QHBoxLayout()
        row_layout.addWidget(ent)
        btn_del = QPushButton("-")
        btn_del.setFixedWidth(20)
        btn_del.clicked.connect(lambda _, n=name: self.remove_custom_token(n))
        row_layout.addWidget(btn_del)
        self.l_tokens.addRow(name + ":", row_layout)
        self.token_inputs[name] = ent

        if hasattr(self, "refresh_local_token_buttons"):
            self.refresh_local_token_buttons()

    def remove_custom_token(self, name):
        if name in self.token_inputs:
            self.token_inputs.pop(name)
            self.refresh_tokens()

    def refresh_com_ports(self):
        ports = [p.device for p in serial.tools.list_ports.comports()]
        self.combo_com.clear()
        if ports:
            self.combo_com.addItems(ports)
        else:
            self.combo_com.addItem("No Ports Found")

    def toggle_flow_axis(self):
        self.ax_flow.set_visible(self.chk_show_flow.isChecked())
        self.canvas.draw()

    def on_filter_change(self, choice):
        if choice in ["Mean", "Median"]:
            self.lbl_filter_param.setText("Window Size (samples):")
            if choice == "Mean":
                self.ent_filter_param.setText("20")
        elif choice == "EMA":
            self.lbl_filter_param.setText("Alpha (0.01 - 1.0):")
            self.ent_filter_param.setText("0.1")
        elif choice == "Butterworth":
            self.lbl_filter_param.setText("Cutoff Freq (Hz):")
            self.ent_filter_param.setText("0.01")
        elif choice == "Adaptive":
            self.lbl_filter_param.setText("Window (Auto-calculated)")

    def connect_serial(self, auto=False):
        port = self.combo_com.currentText()
        if not port or port == "No Ports Found":
            if not auto:
                QMessageBox.critical(self, "Error", "Invalid COM Port.")
            return

        if self.serial_thread and self.serial_thread.isRunning():
            self.serial_thread.stop()
            self.serial_thread.wait()

        baud = 9600
        brand = self.combo_brand.currentText()

        self.serial_thread = SerialWorker(port, baud, brand)
        if hasattr(self.serial_thread, "error_msg"):
            self.lbl_status.setText("Status: Connection Failed")
            self.lbl_status.setStyleSheet("color: #e74c3c;")
            if not auto:
                QMessageBox.critical(self, "Error", f"Could not connect:\n{self.serial_thread.error_msg}")
            return

        self.serial_thread.data_received.connect(self.on_data_received)
        self.serial_thread.start()

        self.lbl_status.setText(f"Status: Connected ({port})")
        self.lbl_status.setStyleSheet("color: #2ecc71; font-weight: bold;")
        self.btn_connect.setText("Connected")
        self.btn_connect.setStyleSheet("background-color: #2ecc71; color: white;")

        if self.app:
            self.app.save_connection(self.tab_name, brand, port)

    def disconnect_serial(self):
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread.wait()
            self.serial_thread = None
        self.lbl_status.setText("Status: Disconnected")
        self.lbl_status.setStyleSheet("color: gray;")
        self.btn_connect.setText("Connect")
        self.btn_connect.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")

    def on_data_received(self, value, unit):
        if not self.recording:
            return

        try:
            intrvl = float(self.ent_interval.text())
        except ValueError:
            intrvl = 1.0

        curr = time.time() - self.start_time
        if (curr - self.last_recorded_time >= intrvl) or len(self.times_sec) == 0:
            self.last_recorded_time = curr

            self.times_sec.append(curr)
            self.times_min.append(curr / 60.0)
            self.weights.append(value)

            ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            self.timestamps.append(ts)

            try:
                is_new = not os.path.exists(self.backup_path)
                with open(self.backup_path, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    if is_new:
                        writer.writerow(["Timestamp", "Duration (min)", "Mass (g)", "Flow Rate (g/min)"])
                    writer.writerow([ts, round(curr / 60.0, 5), value, ""])
            except OSError:
                # Recording carries on, but crash protection is off: say so once.
                if not getattr(self, "_backup_error_logged", False):
                    log.error("Couldn't write the backup file %s", self.backup_path, exc_info=True)
                    self._backup_error_logged = True
                    self.lbl_status.setText("Status: Backup file can't be written (see log)")
                    self.lbl_status.setStyleSheet("color: #e74c3c; font-weight: bold;")

            self.unsaved_changes = True
            if self.app:
                self.app.set_unsaved_state(self.tab_name, True)

            if not self.unit_set:
                self.current_unit = unit
                self.unit_set = True

    def update_gui_components(self):
        n = len(self.times_sec)
        n_items = self.table.rowCount()
        needs_redraw = False

        if n > getattr(self, "last_flow_calc_n", 0):
            self.calculate_flows()
            self.last_flow_calc_n = n
            needs_redraw = True

            if self.recording and self.chk_auto_stop.isChecked():
                if len(self.flow_rates) > 0 and self.flow_rates[-1] is not None:
                    current_flow = self.flow_rates[-1]
                    try:
                        thresh = float(self.ent_auto_stop_thresh.text())
                    except ValueError:
                        thresh = 0.1

                    if abs(current_flow) > thresh:
                        self.last_activity_time = time.time()
                    else:
                        try:
                            stop_min = float(self.ent_auto_stop_min.text())
                        except ValueError:
                            stop_min = 5.0
                        if time.time() - getattr(self, "last_activity_time", time.time()) > (stop_min * 60.0):
                            self.toggle_record()
                            self.txt_notes.append(
                                f"\n[Auto-Stop] Triggered at {datetime.datetime.now().strftime('%H:%M:%S')} due to flow rate < {thresh} for {stop_min} min."
                            )

                            if self.combo_autosave.currentText() == "On Auto-Stop":
                                self.save_excel(auto=True)
                                self.txt_notes.append("[Auto-Save] Data saved to Data folder automatically.")

            if self.recording and self.combo_autosave.currentText() == "Every X Minutes":
                try:
                    autosave_interval = float(self.ent_autosave_min.text())
                except ValueError:
                    autosave_interval = 5.0

                if len(self.times_sec) > 0:
                    elapsed_min = self.times_sec[-1] / 60.0
                    last_autosave = getattr(self, "last_autosave_min", 0.0)
                    if (elapsed_min - last_autosave) >= autosave_interval:
                        self.save_excel(auto=True)
                        self.last_autosave_min = elapsed_min
        if needs_redraw or n > n_items:
            try:
                # Update plot
                f_v = []
                if len(self.times_min) > 0:
                    if self.combo_xaxis.currentText() == "Timestamp":
                        x_data = self.get_wall_clock_data()
                        self.ax_mass.set_xlabel("Elapsed Timestamp (min)")
                    else:
                        x_data = self.times_min
                        self.ax_mass.set_xlabel("Duration (min)")

                    self.line_mass.set_data(list(x_data), list(self.weights))

                    f_v = [f for f in self.flow_rates if f is not None]
                    if self.chk_show_flow.isChecked() and len(f_v) > 0:
                        t_v = [x_data[i] for i in range(len(x_data)) if self.flow_rates[i] is not None]
                        self.line_flow.set_data(list(t_v), list(f_v))

                if self.unit_set:
                    self.ax_mass.set_ylabel(f"Weight ({self.current_unit})")

                if (
                    self.chk_auto_x.isChecked()
                    or self.chk_auto_y_mass.isChecked()
                    or self.chk_auto_y_flow.isChecked()
                ):
                    self.ax_mass.relim()
                    if self.chk_auto_x.isChecked():
                        self.ax_mass.autoscale(enable=True, axis="x", tight=None)
                    if self.chk_auto_y_mass.isChecked():
                        self.ax_mass.autoscale(enable=True, axis="y", tight=None)
                    if self.chk_show_flow.isChecked() and len(f_v) > 0:
                        self.ax_flow.relim()
                        if self.chk_auto_y_flow.isChecked():
                            self.ax_flow.autoscale(enable=True, axis="y", tight=None)

                    xl = self.ax_mass.get_xlim()
                    yl = self.ax_mass.get_ylim()
                    if self.chk_auto_x.isChecked():
                        self.ent_xmin.setText(str(round(xl[0], 2)))
                        self.ent_xmax.setText(str(round(xl[1], 2)))
                    if self.chk_auto_y_mass.isChecked():
                        self.ent_ymin.setText(str(round(yl[0], 2)))
                        self.ent_ymax.setText(str(round(yl[1], 2)))

                    if self.chk_show_flow.isChecked() and len(f_v) > 0:
                        fl = self.ax_flow.get_ylim()
                        if self.chk_auto_y_flow.isChecked():
                            self.ent_flowmin.setText(str(round(fl[0], 2)))
                            self.ent_flowmax.setText(str(round(fl[1], 2)))

                self.canvas.draw_idle()

                # Update Table
                start_idx = n_items
                self.table.setRowCount(n)
                for i in range(start_idx, n):
                    if i < len(self.flow_rates) and self.flow_rates[i] is not None:
                        flow_str = f"{self.flow_rates[i]:.4f}"
                    else:
                        flow_str = ""
                    self.table.setItem(i, 0, QTableWidgetItem(self.timestamps[i].split(" ")[1]))
                    self.table.setItem(i, 1, QTableWidgetItem(f"{self.times_min[i]:.3f}"))
                    self.table.setItem(i, 2, QTableWidgetItem(f"{self.weights[i]:.3f}"))
                    self.table.setItem(i, 3, QTableWidgetItem(flow_str))

                if n > 0:
                    self.table.scrollToBottom()
            except Exception:
                # A drawing problem shouldn't stop recording; log it once per tab.
                if not getattr(self, "_redraw_error_logged", False):
                    log.warning("Couldn't update the chart or table for %s", self.tab_name, exc_info=True)
                    self._redraw_error_logged = True

    def toggle_record(self):
        import datetime

        if not self.recording:
            if len(self.times_sec) == 0:
                self.start_time = time.time()
                self.session_start_time = datetime.datetime.now()
                self.last_autosave_min = 0.0
            if hasattr(self, "wall_clock_min"):
                self.wall_clock_min.clear()
            self.recording = True
            self.last_activity_time = time.time()
            self.ax_mass.set_title(f"{self.tab_name} - Live Weight Data (RECORDING)", color="black")
            self.btn_record.setStyleSheet("background-color: #e74c3c; color: white;")
            self.update_button_text()
        else:
            self.recording = False
            self.ax_mass.set_title(f"{self.tab_name} - Live Weight Data (PAUSED)", color="black")
            self.btn_record.setStyleSheet("background-color: #2ecc71; color: white; font-weight: bold;")
            self.update_button_text()

            if hasattr(self, "chk_save_on_pause") and self.chk_save_on_pause.isChecked():
                self.save_excel(auto=True)
                self.txt_notes.append("[Auto-Save] Data saved automatically upon pause.")
        self.canvas.draw_idle()

    def tare_balance(self):
        if self.serial_thread:
            self.serial_thread.send_tare()

    def clear_data(self):
        self.times_sec.clear()
        self.times_min.clear()
        self.weights.clear()
        self.timestamps.clear()
        self.flow_rates.clear()
        if hasattr(self, "wall_clock_min"):
            self.wall_clock_min.clear()
        self.start_time = time.time()
        import datetime

        self.session_start_time = datetime.datetime.now()
        self.last_activity_time = time.time()
        self.last_recorded_time = 0.0
        self.last_flow_calc_n = 0
        self.last_saved_filepath = None

        self.line_mass.set_data([], [])
        self.line_flow.set_data([], [])
        self.line_fit.set_data([], [])
        self.canvas.draw_idle()

        self.table.setRowCount(0)

    def apply_axis_limits(self):
        if not self.chk_auto_x.isChecked():
            try:
                self.ax_mass.set_xlim(float(self.ent_xmin.text()), float(self.ent_xmax.text()))
            except ValueError:
                pass  # limits not filled in (yet): keep automatic
        if not self.chk_auto_y_mass.isChecked():
            try:
                self.ax_mass.set_ylim(float(self.ent_ymin.text()), float(self.ent_ymax.text()))
            except ValueError:
                pass  # limits not filled in (yet): keep automatic
        if not self.chk_auto_y_flow.isChecked() and self.chk_show_flow.isChecked():
            try:
                self.ax_flow.set_ylim(float(self.ent_flowmin.text()), float(self.ent_flowmax.text()))
            except ValueError:
                pass  # limits not filled in (yet): keep automatic
        self.canvas.draw_idle()

    def manual_apply_filters(self):
        self.last_flow_calc_n = -1
        self.update_gui_components()

    def apply_linear_fit(self):
        if len(self.times_min) < 2:
            return
        try:
            start_min = float(self.ent_fit_start.text())
            end_min = float(self.ent_fit_end.text())
        except ValueError:
            return

        valid_indices = [i for i, t in enumerate(self.times_min) if start_min <= t <= end_min]
        if len(valid_indices) < 2:
            return

        x_vals = [self.times_min[i] for i in valid_indices]
        y_vals = [self.weights[i] for i in valid_indices]

        try:
            slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(x_vals, y_vals)
            fit_y = [slope * x + intercept for x in x_vals]
            self.line_fit.set_data(x_vals, fit_y)
            self.canvas.draw_idle()

            note = f"\n[Linear Fit: {start_min} to {end_min} min] Avg Flow Rate: {slope:.4f} g/min | R²: {r_value**2:.4f}"
            self.txt_notes.append(note)
            self.unsaved_changes = True
            if self.app:
                self.app.set_unsaved_state(self.tab_name, True)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def log_calibration(self):
        try:
            rpm = float(self.ent_rpm.text())
        except ValueError:
            return QMessageBox.critical(self, "Error", "Invalid RPM.")
        if len(self.flow_rates) == 0 or len(self.times_sec) == 0:
            return

        current_time = self.times_sec[-1]
        stable_flows = []
        for i in range(len(self.times_sec) - 1, -1, -1):
            if self.flow_rates[i] is not None:
                if current_time - self.times_sec[i] <= 30.0:
                    stable_flows.append(self.flow_rates[i])
                else:
                    break

        if not stable_flows:
            return
        flow = sum(stable_flows) / len(stable_flows)

        cal_path = os.path.join(
            os.getcwd(), "Data Backups", f"{self.tab_name.replace(' ', '_')}_Calibration.csv"
        )
        is_new = not os.path.exists(cal_path)

        try:
            with open(cal_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if is_new:
                    writer.writerow(
                        ["Timestamp", "Pump RPM", "Avg Flow Rate (g/min)", "Averaging Window (s)"]
                    )
                ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                writer.writerow([ts, rpm, round(flow, 4), "30.0"])
            QMessageBox.information(self, "Success", f"Logged: {round(flow, 4)} g/min")
        except OSError as e:
            log.exception("Couldn't write the calibration file %s", cal_path)
            QMessageBox.critical(self, "Error", f"Couldn't save the calibration point:\n{e}")

    def browse_save_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Save Folder", self.ent_save_folder.toPlainText().replace("\n", "").strip()
        )
        if folder:
            self.ent_save_folder.setPlainText(folder)

    def toggle_autosave_interval(self):
        self.ent_autosave_min.setEnabled(self.combo_autosave.currentText() == "Every X Minutes")

    def toggle_template_source(self):
        use_global = self.chk_use_global_template.isChecked()
        self.ent_save_template.setEnabled(not use_global)
        if use_global and self.app:
            self.ent_save_template.setText(
                self.app.config.get("global_filename_template", "<Tab Name>_<Date>_<Time>")
            )

    def close_tab(self):
        if self.recording:
            QMessageBox.warning(self, "Warning", "Stop recording before closing.")
            return
        if self.app:
            self.app.close_tab(self)

    def request_add_tab(self):
        if self.app:
            self.app.add_tab(self.ent_new_tab.text())
            self.ent_new_tab.clear()

    def request_rename_tab(self):
        if self.app:
            self.app.rename_tab()
