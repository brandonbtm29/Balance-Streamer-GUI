import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QRect
from multi_balance_stream import GlobalSavingSettingsDialog

app = QApplication(sys.argv)
dialog = GlobalSavingSettingsDialog()
dialog.show()

def dump_tree(w, indent=0):
    geom = w.geometry()
    # Also print the class name and any text if it has it
    text = getattr(w, "text", lambda: "")()
    title = getattr(w, "title", lambda: "")()
    
    info = f"{w.__class__.__name__} ({w.objectName()}) geom={geom}"
    if text: info += f" text='{text}'"
    if title: info += f" title='{title}'"
    print("  " * indent + info)
    for c in w.children():
        if hasattr(c, "geometry") and c.isWidgetType():
            dump_tree(c, indent + 1)

dump_tree(dialog)
app.quit()
