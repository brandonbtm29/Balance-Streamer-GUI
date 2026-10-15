"""The Settings tab: application settings, panel order, global save settings and help."""

from PyQt6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import settings_location

from .paths import APP_DIR, DATA_DIR, SETTINGS_FILES
from .widgets import CollapsibleBox, ReorderPanelsWidget


class GlobalSavingSettingsWidget(QWidget):
    def __init__(self, parent=None, config=None):
        super().__init__(parent)

        self.config = config or {}

        main_layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        # --- TAB 1: General Settings ---
        tab_general = QWidget()
        l_general = QVBoxLayout(tab_general)

        # Save Folder
        gb_folder = CollapsibleBox("Global Default Save Folder")
        l_folder = QVBoxLayout()
        gb_folder.setLayout(l_folder)
        self.ent_folder = QTextEdit(self.config.get("global_default_save_folder", "Data"))
        self.ent_folder.setFixedHeight(45)
        btn_browse = QPushButton("Browse")
        btn_browse.clicked.connect(self.browse_folder)
        l_folder.addWidget(self.ent_folder)
        l_folder.addWidget(btn_browse)
        l_general.addWidget(gb_folder)

        # Template
        gb_temp = CollapsibleBox("Global Filename Template")
        l_temp = QVBoxLayout()
        gb_temp.setLayout(l_temp)

        form_layout = QFormLayout()
        form_layout.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        self.ent_template = QLineEdit(self.config.get("global_filename_template", "<Tab Name>_<Date>_<Time>"))
        form_layout.addRow("Filename Format:", self.ent_template)
        l_temp.addLayout(form_layout)

        l_temp.addWidget(QLabel("Click a token below to insert it at the cursor position:"))

        self.grid_buttons = QGridLayout()
        l_temp.addLayout(self.grid_buttons)
        l_general.addWidget(gb_temp)
        l_general.addStretch()

        self.tabs.addTab(tab_general, "General & Template")

        # --- TAB 2: Metadata Tokens ---
        tab_tokens = QWidget()
        l_tokens_wrapper = QVBoxLayout(tab_tokens)

        scroll_tokens = QScrollArea()
        scroll_tokens.setWidgetResizable(True)
        scroll_content = QWidget()

        self.layout_tokens = QVBoxLayout(scroll_content)
        self.token_rows = []
        self.token_button_refs = []

        btn_add_token = QPushButton("+ Add Custom Token")
        btn_add_token.clicked.connect(lambda: self.add_token_row("", ""))
        self.layout_tokens.addWidget(btn_add_token)

        global_tokens = self.config.get(
            "global_tokens",
            [
                {"name": "Column #/Name", "value": ""},
                {"name": "Material", "value": ""},
                {"name": "Flow rate", "value": ""},
                {"name": "Bed length", "value": ""},
                {"name": "Run #", "value": ""},
                {"name": "(De)Sorption", "value": ""},
            ],
        )

        existing_names = [t.get("name") for t in global_tokens if t.get("name")]
        if "Column Name" in existing_names:
            for t in global_tokens:
                if t.get("name") == "Column Name":
                    t["name"] = "Column #/Name"
        if "(De)Sorption" not in existing_names:
            global_tokens.append({"name": "(De)Sorption", "value": ""})

        for t in global_tokens:
            self.add_token_row(t.get("name", ""), t.get("value", ""))

        scroll_tokens.setWidget(scroll_content)
        l_tokens_wrapper.addWidget(scroll_tokens)

        self.tabs.addTab(tab_tokens, "Metadata Tokens")
        self.refresh_token_buttons()

        # Buttons
        btn_layout = QHBoxLayout()
        btn_ok = QPushButton("Save Globally")

        btn_layout.addWidget(btn_ok)
        main_layout.addLayout(btn_layout)

        btn_ok.clicked.connect(self.apply_settings)

    def apply_settings(self):
        self.config["global_default_save_folder"] = self.ent_folder.toPlainText().replace("\n", "").strip()
        self.config["global_filename_template"] = self.ent_template.text()
        self.config["global_tokens"] = self.get_tokens()
        if hasattr(self.parent(), "app_ref"):
            self.parent().app_ref.save_config()
            for tab in self.parent().app_ref.tab_objects:
                if hasattr(tab, "refresh_tokens"):
                    tab.refresh_tokens()

    def browse_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Save Folder", self.ent_folder.toPlainText().replace("\n", "").strip()
        )
        if folder:
            self.ent_folder.setPlainText(folder)

    def add_token_row(self, name, value):
        row_widget = QWidget()
        row_layout = QHBoxLayout(row_widget)
        row_layout.setContentsMargins(0, 0, 0, 0)

        ent_name = QLineEdit(name)
        ent_name.setPlaceholderText("Token Name")
        ent_name.textChanged.connect(self.refresh_token_buttons)
        ent_value = QLineEdit(value)
        ent_value.setPlaceholderText("Value")

        btn_remove = QPushButton("X")
        btn_remove.setFixedWidth(30)
        btn_remove.setStyleSheet("background-color: #e74c3c; color: white;")

        row_layout.addWidget(ent_name)
        row_layout.addWidget(ent_value)
        row_layout.addWidget(btn_remove)

        idx = self.layout_tokens.count() - 1
        self.layout_tokens.insertWidget(idx, row_widget)

        row_data = (row_widget, ent_name, ent_value)
        self.token_rows.append(row_data)

        btn_remove.clicked.connect(lambda: self.remove_token_row(row_data))
        self.refresh_token_buttons()

    def remove_token_row(self, row_data):
        row_widget, ent_name, ent_value = row_data
        if row_data in self.token_rows:
            self.token_rows.remove(row_data)
        self.layout_tokens.removeWidget(row_widget)
        row_widget.hide()
        row_widget.setParent(None)
        row_widget.deleteLater()
        self.refresh_token_buttons()

    def refresh_token_buttons(self):
        while self.grid_buttons.count():
            item = self.grid_buttons.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        self.token_button_refs = []

        tokens = ["Tab Name", "Date", "Time", "Start Date", "Start Time"]
        for _, ent_name, _ in self.token_rows:
            n = ent_name.text().strip()
            if n and n not in tokens:
                tokens.append(n)

        row = 0
        col = 0
        for tok in tokens:
            btn = QPushButton(f"<{tok}>")
            btn.clicked.connect(lambda checked, t=tok: self.ent_template.insert(f"<{t}>"))
            self.grid_buttons.addWidget(btn, row, col)
            self.token_button_refs.append(btn)
            col += 1
            if col > 3:
                col = 0
                row += 1

    def get_tokens(self):
        return [{"name": n.text(), "value": v.text()} for _, n, v in self.token_rows if n.text().strip()]


class SettingsTab(QWidget):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref
        self.tab_name = "Settings"

        main_layout = QHBoxLayout(self)

        # Sidebar
        self.sidebar = QListWidget()
        self.sidebar.setMaximumWidth(220)
        self.sidebar.setStyleSheet("QListWidget { font-size: 14px; } QListWidget::item { padding: 10px; }")

        # Stack
        self.stack = QStackedWidget()

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.stack)

        # 1. Application Settings
        page_app = QWidget()
        l_app = QVBoxLayout(page_app)

        self.chk_btn_text = QCheckBox("Show Button Text")
        self.chk_btn_text.setChecked(self.app_ref.config.get("show_button_text", False))
        self.chk_btn_text.clicked.connect(self.toggle_button_text)
        l_app.addWidget(self.chk_btn_text)

        self.chk_dark_mode = QCheckBox("Dark Mode")
        self.chk_dark_mode.setChecked(self.app_ref.config.get("dark_mode", True))
        self.chk_dark_mode.clicked.connect(self.toggle_theme)
        l_app.addWidget(self.chk_dark_mode)

        l_app.addWidget(
            settings_location.settings_folder_box(
                APP_DIR,
                DATA_DIR,
                SETTINGS_FILES,
                save_cb=lambda: (
                    [
                        t.save_tab_settings()
                        for t in self.app_ref.tab_objects
                        if hasattr(t, "save_tab_settings")
                    ],
                    self.app_ref.save_config(),
                ),
                restart_cb=self.app_ref.restart_app,
            )
        )
        btn_restart = QPushButton("Restart Application")
        btn_restart.clicked.connect(self.app_ref.restart_app)
        l_app.addWidget(btn_restart)
        l_app.addStretch()

        self.sidebar.addItem("⚙ Application Settings")
        self.stack.addWidget(page_app)

        # 2. Panel Management
        page_panels = QWidget()
        l_panels = QVBoxLayout(page_panels)
        self.panel_widget = ReorderPanelsWidget(self.app_ref)
        l_panels.addWidget(self.panel_widget)

        self.sidebar.addItem("🗂 Panel Management")
        self.stack.addWidget(page_panels)

        # 3. Global Settings & Metadata
        page_global = QWidget()
        l_global = QVBoxLayout(page_global)

        from PyQt6.QtWidgets import QFrame

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.global_widget = GlobalSavingSettingsWidget(self, self.app_ref.config)
        scroll.setWidget(self.global_widget)

        l_global.addWidget(scroll)

        self.sidebar.addItem("💾 Global Settings")
        self.stack.addWidget(page_global)

        # 4. Help
        page_help = QWidget()
        l_help = QVBoxLayout(page_help)

        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setHtml("""
        <h2 style='color: #3498db;'>Hardware Setup: Continuous Print Mode</h2>
        <p>For the Balance Streamer to read live data over USB/RS232, your balance must be configured to output data continuously.</p>
        <ul>
            <li><b>Ohaus:</b> Go to Menu > Print > Auto Print > Continuous. Set baud rate to 9600. (<a href="https://dmx.ohaus.com/WorkArea/showcontent.aspx?id=4294974227">Ohaus Manual</a>)</li>
            <li><b>Mettler Toledo:</b> Go to Settings > System > Peripherals > Host. Set Send Mode to "Continuous". (<a href="https://www.mt.com/us/en/home/library/operating-instructions/laboratory-weighing/MS-TS_OI.html">Mettler Manual</a>)</li>
            <li><b>Adam Equipment:</b> Go to RS-232 Menu > PC > Continuous. (<a href="https://www.adamequipment.com/media/docs/Print/EN/Manuals/Nimbus_Manual.pdf">Adam Manual</a>)</li>
            <li><b>Generic / Other:</b> Refer to your manufacturer's manual. Look for settings named "Auto-Print", "Continuous Send", or "Stream Data".</li>
        </ul>
        <br>
        <h2 style='color: #3498db;'>Derivative Engine</h2>
        <p>This application uses a <b>Savitzky-Golay (SavGol)</b> filter to compute the flow rate (derivative) from the raw mass data. Savitzky-Golay fits a local polynomial to the data points, which smooths out high-frequency noise while calculating a highly accurate derivative.</p>
        <h2 style='color: #3498db;'>Secondary Smoothing</h2>
        <p>Because flow rate is a derivative, it can be inherently noisy. Secondary Smoothing applies a final low-pass filter to the calculated flow rate for better visualization.</p>
        <ul>
            <li><b>Mean / Median:</b> Standard moving window averages.</li>
            <li><b>EMA:</b> Exponential Moving Average, gives more weight to recent data.</li>
            <li><b>Butterworth:</b> A sophisticated signal processing filter for extremely smooth lines.</li>
            <li><b>Adaptive:</b> Automatically adjusts its window size based on your pump RPM and roller count.</li>
        </ul>
        """)
        l_help.addWidget(tb)

        self.sidebar.addItem("❓ Help & About")
        self.stack.addWidget(page_help)

        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

    def toggle_button_text(self, checked):
        self.app_ref.config["show_button_text"] = checked
        self.app_ref.save_config()
        for tab in self.app_ref.tab_objects:
            if hasattr(tab, "update_gui_components"):
                tab.update_gui_components()

    def toggle_theme(self, checked):
        self.app_ref.config["dark_mode"] = checked
        self.app_ref.save_config()
        self.app_ref.apply_theme()
