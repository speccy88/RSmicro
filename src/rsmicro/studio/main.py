from __future__ import annotations
import argparse,sys
from rsmicro import __version__
def parser():
 p=argparse.ArgumentParser(prog="rsmicro-studio",description="RSmicro Studio engineering environment")
 p.add_argument("project",nargs="?"); p.add_argument("--new",action="store_true"); p.add_argument("--safe-mode",action="store_true"); p.add_argument("--reset-layout",action="store_true"); p.add_argument("--offscreen",action="store_true"); p.add_argument("--verify",action="store_true"); p.add_argument("--run-duration",type=float,default=2); p.add_argument("--version",action="version",version=__version__); return p
def main(argv=None):
 args=parser().parse_args(argv)
 try:
  from PySide6.QtCore import QSettings,QTimer
  from PySide6.QtWidgets import QApplication
  from .main_window import MainWindow
  from .session import ProjectSession
 except ImportError as exc: print("PySide6 is required for RSmicro Studio: "+str(exc),file=sys.stderr); return 2
 if args.offscreen: QApplication.setAttribute(__import__('PySide6').QtCore.Qt.ApplicationAttribute.AA_Use96Dpi)
 app=QApplication(sys.argv[:1]); app.setOrganizationName("RSmicro"); app.setApplicationName("Studio"); settings=QSettings(); session=ProjectSession()
 try:
  if args.project: session.open(args.project)
 except Exception as exc: print(f"Unable to open project: {exc}",file=sys.stderr); return 2
 window=MainWindow(session,settings)
 if session.project: window.load_project()
 window.show()
 if args.verify: QTimer.singleShot(max(1,int(args.run_duration*1000)),app.quit)
 return app.exec()
if __name__=="__main__": raise SystemExit(main())
