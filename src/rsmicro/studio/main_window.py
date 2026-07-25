from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction, QStandardItem, QStandardItemModel, QUndoStack
from PySide6.QtWidgets import (QDockWidget,QGraphicsView,QLabel,QMainWindow,QMenu,QPlainTextEdit,QTabWidget,QTableView,QTreeView)
from .ladder import LadderScene

class MainWindow(QMainWindow):
 def __init__(self,session,settings):
  super().__init__(); self.session=session; self.settings=settings; self.undo_stack=QUndoStack(self); self.thread_pool=QThreadPool(self)
  self.setWindowTitle("RSmicro Studio"); self.resize(1280,800); self.tabs=QTabWidget(); self.setCentralWidget(self.tabs)
  self.tree=QTreeView(); self.tree_model=QStandardItemModel(); self.tree_model.setHorizontalHeaderLabels(["Project"]); self.tree.setModel(self.tree_model)
  self._dock("Project Explorer",self.tree,Qt.DockWidgetArea.LeftDockWidgetArea)
  self._dock("Properties",QTableView(),Qt.DockWidgetArea.RightDockWidgetArea)
  for title in ("Compile Diagnostics","Output","Online Monitor","Controller Diagnostics","Alarm Summary","Historian Results"):
   self._dock(title,QPlainTextEdit(),Qt.DockWidgetArea.BottomDockWidgetArea)
  self._actions(); self.statusBar().showMessage("Offline — no forces — broker disconnected")
 def _dock(self,title,widget,area): d=QDockWidget(title,self); d.setObjectName(title); d.setWidget(widget); self.addDockWidget(area,d)
 def _actions(self):
  names={"File":["New","Open","Save","Save As","Close"],"Edit":["Undo","Redo"],"View":["Reset Window Layout"],
   "Project":["Validate","Compile"],"Logic":["Add Rung","Delete Rung"],"Controller":["Connect","Download","RUN","PROGRAM","TEST","Disconnect"],
   "Simulation":["Start Simulation","Stop Simulation","One Scan"],"SCADA":["New Screen","Preview"],"Tools":["Settings"],"Help":["About"]}
  bar=self.menuBar()
  for menu_name,actions in names.items():
   menu=bar.addMenu(menu_name)
   for name in actions:
    action=QAction(name,self); action.setEnabled(name in {"New","Open","About","Settings","Reset Window Layout","Undo","Redo"} or self.session.project is not None)
    if name=="Undo": action.triggered.connect(self.undo_stack.undo)
    if name=="Redo": action.triggered.connect(self.undo_stack.redo)
    menu.addAction(action)
 def load_project(self):
  p=self.session.project; self.tree_model.removeRows(0,self.tree_model.rowCount()); root=QStandardItem(p.name); root.setData(p.project_id,Qt.ItemDataRole.UserRole)
  controllers=QStandardItem("Controllers")
  for c in p.controllers:
   item=QStandardItem(c.name); item.setData(c.controller_id,Qt.ItemDataRole.UserRole); controllers.appendRow(item)
   for program in c.programs:
    for routine in program.routines:
     scene=LadderScene(); scene.load_routine(routine); self.tabs.addTab(QGraphicsView(scene),routine.name)
  root.appendRow(controllers); root.appendRow(QStandardItem("Deployments")); root.appendRow(QStandardItem("SCADA")); root.appendRow(QStandardItem("Build Artifacts")); self.tree_model.appendRow(root); self.tree.expandAll()
