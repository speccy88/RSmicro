from PySide6.QtWidgets import QMainWindow,QWidget,QLabel
from .widgets import create_widget
class ScadaWindow(QMainWindow):
 def __init__(self,screen,no_write=False):
  super().__init__(); self.scada_screen=screen; self.no_write=no_write; self.setWindowTitle(f"RSmicro SCADA — {screen.name}")
  canvas=QWidget(); canvas.setMinimumSize(screen.width,screen.height); canvas.setStyleSheet(f"background:{screen.background}")
  self.screen_widgets: dict[str, QWidget] = {}
  for obj in sorted(screen.objects,key=lambda o:o.z_order):
   widget=create_widget(obj); widget.setParent(canvas); g=obj.geometry; widget.setGeometry(int(g.get('x',0)),int(g.get('y',0)),int(g.get('width',120)),int(g.get('height',40))); widget.setVisible(obj.visible); widget.setEnabled(not obj.locked and not (no_write and obj.type in {'pushbutton','numeric_input'})); self.screen_widgets[obj.object_id]=widget
  self.setCentralWidget(canvas); self.statusBar().showMessage("Broker: disconnected | Quality: STALE | Forces: 0 | Alarms: 0")
