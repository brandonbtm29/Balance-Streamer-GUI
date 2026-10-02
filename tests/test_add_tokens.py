import sys
from PyQt6.QtWidgets import QApplication
from multi_balance_stream import GlobalSavingSettingsDialog
from PyQt6.QtCore import QTimer

app = QApplication(sys.argv)
dialog = GlobalSavingSettingsDialog(None, {})
dialog.show()

def run_test():
    # Click "Add Custom Token" 5 times
    btn_add = dialog.layout_tokens.itemAt(0).widget()
    for _ in range(5):
        btn_add.click()
    
    # Print tree
    def print_tree(widget, indent=0):
        print(" " * indent + f"{widget.__class__.__name__} geometry: {widget.geometry()} global: {widget.mapToGlobal(widget.pos())}")
        for child in widget.children():
            if hasattr(child, 'geometry') and child.isWidgetType():
                print_tree(child, indent + 2)

    print_tree(dialog)
    app.quit()

QTimer.singleShot(500, run_test)
sys.exit(app.exec())
