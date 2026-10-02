import sys
from PyQt6.QtWidgets import QApplication
from multi_balance_stream import GlobalSavingSettingsDialog

app = QApplication(sys.argv)
dialog = GlobalSavingSettingsDialog(None, {})
dialog.show()

# Find the group boxes
gbs = dialog.findChildren(type(dialog.layout().itemAt(0).widget())) # No, that's not it. Let's just iterate
def print_tree(widget, indent=0):
    print(" " * indent + f"{widget.__class__.__name__} geometry: {widget.geometry()} global: {widget.mapToGlobal(widget.pos())}")
    for child in widget.children():
        if hasattr(child, 'geometry') and child.isWidgetType():
            print_tree(child, indent + 2)

print_tree(dialog)

sys.exit(0)
