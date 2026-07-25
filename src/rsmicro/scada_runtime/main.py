from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from rsmicro import __version__
from rsmicro.model import load_project
from rsmicro.scada_screen import Screen,validate_screen
def parser():
 p=argparse.ArgumentParser(prog="rsmicro-scada",description="Standalone RSmicro SCADA operator runtime")
 p.add_argument("--project",required=True); p.add_argument("--screen",required=True); p.add_argument("--host",default="127.0.0.1"); p.add_argument("--port",type=int,default=7590); p.add_argument("--role",choices=("viewer","operator","engineering"),default="viewer"); p.add_argument("--fullscreen",action="store_true"); p.add_argument("--windowed",action="store_true"); p.add_argument("--width",type=int); p.add_argument("--height",type=int); p.add_argument("--kiosk",action="store_true"); p.add_argument("--no-write",action="store_true"); p.add_argument("--log-level",default="INFO"); p.add_argument("--json-logs",action="store_true"); p.add_argument("--verify",action="store_true"); p.add_argument("--run-duration",type=float,default=3); p.add_argument("--version",action="version",version=__version__); return p
def _screens(project,path):
 result=[]
 for value in project.scada.screens:
  if isinstance(value,str): value=json.loads((Path(path).parent/value).read_text())
  result.append(Screen.from_dict(value))
 return result
def main(argv=None):
 args=parser().parse_args(argv)
 try:
  from PySide6.QtCore import QTimer
  from PySide6.QtWidgets import QApplication
  from .window import ScadaWindow
 except ImportError as exc: print("PySide6 is required for RSmicro SCADA: "+str(exc),file=sys.stderr); return 2
 try: project=load_project(args.project); screens=_screens(project,args.project); screen=next(x for x in screens if x.screen_id==args.screen or x.name==args.screen)
 except Exception as exc: print(f"Cannot load SCADA screen: {exc}",file=sys.stderr); return 2
 errors=validate_screen(screen,{t.tag_id for c in project.controllers for t in c.tags})
 if errors: print("Invalid SCADA screen: "+"; ".join(errors),file=sys.stderr); return 2
 app=QApplication(sys.argv[:1]); window=ScadaWindow(screen,args.no_write or args.role=="viewer");
 if args.width and args.height: window.resize(args.width,args.height)
 if args.fullscreen or args.kiosk: window.showFullScreen()
 else: window.show()
 if args.verify: QTimer.singleShot(max(1,int(args.run_duration*1000)),app.quit)
 return app.exec()
if __name__=="__main__": raise SystemExit(main())
