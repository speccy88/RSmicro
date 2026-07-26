from PySide6.QtWidgets import QMainWindow, QWidget

from .widgets import create_widget


class ScadaWindow(QMainWindow):
    def __init__(self, screen, no_write=False):
        super().__init__()
        self.scada_screen = screen
        self.no_write = no_write
        self.setWindowTitle(f"RSmicro SCADA — {screen.name}")
        canvas = QWidget()
        canvas.setMinimumSize(screen.width, screen.height)
        canvas.setStyleSheet(f"background:{screen.background}")
        self.screen_widgets: dict[str, QWidget] = {}
        for obj in sorted(screen.objects, key=lambda item: item.z_order):
            widget = create_widget(obj)
            widget.setParent(canvas)
            geometry = obj.geometry
            widget.setGeometry(
                int(geometry.get("x", 0)),
                int(geometry.get("y", 0)),
                int(geometry.get("width", 120)),
                int(geometry.get("height", 40)),
            )
            widget.setVisible(obj.visible)
            widget.setEnabled(
                not obj.locked
                and not (no_write and obj.type in {"pushbutton", "numeric_input"})
            )
            self.screen_widgets[obj.object_id] = widget
        self.setCentralWidget(canvas)
        self.statusBar().setStyleSheet(
            "QStatusBar{background:#020617;color:#94a3b8;padding:6px;font-size:13px;}"
        )
        self.statusBar().showMessage(
            "Offline preview • Broker: disconnected • Quality: STALE • "
            "Forces: 0 • Alarms: unavailable"
        )
