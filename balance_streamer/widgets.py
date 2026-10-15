"""Small reusable widgets: collapsible panels and the panel-order editor."""

from PyQt6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CollapsibleBox(QWidget):
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.btn_toggle = QPushButton(f"▼ {title}")
        self.btn_toggle.setStyleSheet(
            "text-align: left; font-weight: bold; padding: 5px; background-color: transparent; border: none;"
        )
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(False)  # False = expanded
        self.btn_toggle.toggled.connect(self.on_toggle)
        self.layout.addWidget(self.btn_toggle)

        self.content_widget = QWidget()
        self.layout.addWidget(self.content_widget)

        self.title_text = title

    def setLayout(self, layout):
        layout.setContentsMargins(5, 5, 5, 5)
        self.content_widget.setLayout(layout)

    def on_toggle(self, checked):
        self.btn_toggle.setText(f"▶ {self.title_text}" if checked else f"▼ {self.title_text}")
        self.content_widget.setVisible(not checked)

    def set_collapsed(self, collapsed=True):
        self.btn_toggle.setChecked(collapsed)


class ReorderPanelsWidget(QWidget):
    def __init__(self, app_ref, parent=None):
        super().__init__(parent)
        self.app_ref = app_ref

        layout = QVBoxLayout(self)

        lbl = QLabel("Drag and drop to reorder panels. The app will restart when applied.")
        layout.addWidget(lbl)

        lists_layout = QHBoxLayout()

        left_grp = QGroupBox("Left Panel")
        left_lay = QVBoxLayout(left_grp)
        self.list_left = QListWidget()
        self.list_left.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        left_order = self.app_ref.config.get(
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
        self.list_left.addItems(left_order)
        left_lay.addWidget(self.list_left)
        lists_layout.addWidget(left_grp)

        right_grp = QGroupBox("Right Panel")
        right_lay = QVBoxLayout(right_grp)
        self.list_right = QListWidget()
        self.list_right.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        right_order = self.app_ref.config.get(
            "right_panel_order", ["Tab Management", "Connection", "Experiment Notes"]
        )
        self.list_right.addItems(right_order)
        right_lay.addWidget(self.list_right)
        lists_layout.addWidget(right_grp)

        layout.addLayout(lists_layout)

        btn_layout = QHBoxLayout()
        btn_apply = QPushButton("Apply and Restart")
        btn_apply.clicked.connect(self.apply)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_apply)
        layout.addLayout(btn_layout)

    def apply(self):
        new_left = [self.list_left.item(i).text() for i in range(self.list_left.count())]
        new_right = [self.list_right.item(i).text() for i in range(self.list_right.count())]
        self.app_ref.config["left_panel_order"] = new_left
        self.app_ref.config["right_panel_order"] = new_right
        self.app_ref.save_config()
        pass

        # Restart the app
        import sys

        from PyQt6.QtCore import QProcess
        from PyQt6.QtWidgets import QApplication

        QProcess.startDetached(sys.executable, sys.argv)
        QApplication.instance().quit()
