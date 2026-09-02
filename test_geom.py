import sys
from PyQt6.QtWidgets import QApplication
from multi_balance_stream import GlobalSavingSettingsDialog

app = QApplication(sys.argv)
dialog = GlobalSavingSettingsDialog(None, {})
dialog.show()

# Print geometries
print("Dialog size:", dialog.size())
print("ScrollArea size:", dialog.findChild(type(dialog.layout().itemAt(0).widget())).size())
print("ent_template geometry:", dialog.ent_template.geometry())
print("ent_template pos in global:", dialog.ent_template.mapToGlobal(dialog.ent_template.pos()))
print("ent_template isVisible:", dialog.ent_template.isVisible())

sys.exit(0)
