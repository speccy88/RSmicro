from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction, QPainter, QStandardItem, QStandardItemModel, QUndoStack
from PySide6.QtWidgets import (
    QDockWidget,
    QGraphicsView,
    QMainWindow,
    QPlainTextEdit,
    QTabWidget,
    QTableView,
    QTreeView,
)

from .ladder import LadderScene


class MainWindow(QMainWindow):
    def __init__(self, session, settings):
        super().__init__()
        self.session = session
        self.settings = settings
        self.undo_stack = QUndoStack(self)
        self.thread_pool = QThreadPool(self)
        self.ladder_scenes: list[LadderScene] = []
        self.ladder_views: list[QGraphicsView] = []
        self.setWindowTitle("RSmicro Studio")
        self.resize(1280, 800)
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.setCentralWidget(self.tabs)

        self.tree = QTreeView()
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["Project"])
        self.tree.setModel(self.tree_model)
        self._dock("Project Explorer", self.tree, Qt.DockWidgetArea.LeftDockWidgetArea)
        self._dock("Properties", QTableView(), Qt.DockWidgetArea.RightDockWidgetArea)

        lower_docks: list[QDockWidget] = []
        for title in (
            "Compile Diagnostics",
            "Output",
            "Online Monitor",
            "Controller Diagnostics",
            "Alarm Summary",
            "Historian Results",
        ):
            pane = QPlainTextEdit()
            pane.setReadOnly(True)
            pane.setPlainText(self._pane_message(title))
            lower_docks.append(self._dock(title, pane, Qt.DockWidgetArea.BottomDockWidgetArea))
        for dock in lower_docks[1:]:
            self.tabifyDockWidget(lower_docks[0], dock)
        lower_docks[0].raise_()

        self._actions()
        self.statusBar().showMessage(
            "Offline project view — compiler and local native simulation are available"
        )

    @staticmethod
    def _pane_message(title: str) -> str:
        messages = {
            "Compile Diagnostics": "No compilation has been run in this Studio session.",
            "Output": "Open a canonical project, then use the documented CLI for validated compile/simulation workflows.",
            "Online Monitor": "Offline — live node and broker monitoring are not connected.",
            "Controller Diagnostics": "No controller session.",
            "Alarm Summary": "No live alarm source.",
            "Historian Results": "No historian query has been run.",
        }
        return messages[title]

    def _dock(self, title, widget, area):
        dock = QDockWidget(title, self)
        dock.setObjectName(title)
        dock.setWidget(widget)
        self.addDockWidget(area, dock)
        return dock

    def _actions(self):
        names = {
            "File": ["New", "Open", "Save", "Save As", "Close"],
            "Edit": ["Undo", "Redo"],
            "View": ["Reset Window Layout"],
            "Project": ["Validate", "Compile"],
            "Logic": ["Add Rung", "Delete Rung"],
            "Controller": ["Connect", "Download", "RUN", "PROGRAM", "TEST", "Disconnect"],
            "Simulation": ["Start Simulation", "Stop Simulation", "One Scan"],
            "SCADA": ["New Screen", "Preview"],
            "Tools": ["Settings"],
            "Help": ["About"],
        }
        bar = self.menuBar()
        for menu_name, actions in names.items():
            menu = bar.addMenu(menu_name)
            for name in actions:
                action = QAction(name, self)
                action.setEnabled(
                    name in {
                        "New", "Open", "About", "Settings", "Reset Window Layout", "Undo", "Redo"
                    }
                    or self.session.project is not None
                )
                if name == "Undo":
                    action.triggered.connect(self.undo_stack.undo)
                if name == "Redo":
                    action.triggered.connect(self.undo_stack.redo)
                menu.addAction(action)

    def load_project(self):
        project = self.session.project
        self.tree_model.removeRows(0, self.tree_model.rowCount())
        root = QStandardItem(project.name)
        root.setData(project.project_id, Qt.ItemDataRole.UserRole)
        controllers = QStandardItem("Controllers")
        for controller in project.controllers:
            controller_item = QStandardItem(controller.name)
            controller_item.setData(controller.controller_id, Qt.ItemDataRole.UserRole)
            controllers.appendRow(controller_item)
            for program in controller.programs:
                program_item = QStandardItem(program.name)
                controller_item.appendRow(program_item)
                for routine in program.routines:
                    routine_item = QStandardItem(routine.name)
                    program_item.appendRow(routine_item)
                    view = QGraphicsView()
                    scene = LadderScene(view)
                    scene.load_routine(routine)
                    self.ladder_scenes.append(scene)
                    self.ladder_views.append(view)
                    view.setScene(scene)
                    view.setRenderHint(QPainter.RenderHint.Antialiasing)
                    self.tabs.addTab(view, f"{controller.name} • {routine.name}")
        root.appendRow(controllers)
        root.appendRow(QStandardItem("Deployments"))
        root.appendRow(QStandardItem("SCADA Screens"))
        root.appendRow(QStandardItem("Build Artifacts"))
        self.tree_model.appendRow(root)
        self.tree.expandAll()

    def reset_ladder_views(self):
        """Open every routine at rung one rather than the scene midpoint."""
        for view in self.ladder_views:
            view.horizontalScrollBar().setValue(view.horizontalScrollBar().minimum())
            view.verticalScrollBar().setValue(view.verticalScrollBar().minimum())
