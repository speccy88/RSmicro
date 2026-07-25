from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .diagnostics import Severity
from .migration import migrate_legacy
from .model import load_project,validate_project
from .schemas import validate_schema

def diagnostics(path):
 try: raw=json.loads(Path(path).read_text(encoding="utf-8"))
 except (OSError,json.JSONDecodeError) as e: return None, [{"severity":"ERROR","code":"JSON_INVALID","message":str(e),"source_file":str(path)}]
 sd=validate_schema(raw,source_file=str(path))
 try: p=load_project(path); ds=sd+validate_project(p,str(path))
 except Exception as e: return None,[*map(lambda x:x.to_dict(),sd),{"severity":"ERROR","code":"MODEL_INVALID","message":str(e),"source_file":str(path)}]
 return p,[x.to_dict() for x in ds]
def main(argv=None):
 ap=argparse.ArgumentParser(prog="rsmicro",description="RSmicro canonical project tools"); sp=ap.add_subparsers(dest="command",required=True)
 v=sp.add_parser("validate"); v.add_argument("project"); v.add_argument("--format",choices=["text","json"],default="text")
 m=sp.add_parser("migrate-v1"); m.add_argument("legacy_project"); m.add_argument("--output",required=True); m.add_argument("--force",action="store_true")
 s=sp.add_parser("show-project"); s.add_argument("project")
 a=ap.parse_args(argv)
 if a.command=="validate":
  _,ds=diagnostics(a.project)
  if a.format=="json": print(json.dumps(ds,indent=2))
  elif ds:
   for d in ds: print(f"{d['severity']} {d['code']} {d.get('path','')}: {d['message']}")
  else: print(f"Valid RSmicro project: {a.project}")
  return 1 if any(d["severity"]=="ERROR" for d in ds) else 0
 if a.command=="migrate-v1":
  out=Path(a.output)
  if out.exists() and not a.force: print(f"error: output exists: {out}",file=sys.stderr); return 2
  p,r=migrate_legacy(a.legacy_project,out); rp=Path(str(out)+".migration.json"); rp.write_text(json.dumps(r.to_dict(),indent=2)+"\n",encoding="utf-8")
  print(f"Migrated {r.objects_migrated.get('rungs',0)} rungs and {r.objects_migrated.get('tags',0)} tags to {out}")
  print(f"Report: {rp}"); return 1 if r.errors else 0
 p,ds=diagnostics(a.project)
 if p is None: print("Invalid project"); return 1
 tags=sum(len(c.tags) for c in p.controllers); routines=sum(len(x.routines) for c in p.controllers for x in c.programs); rungs=sum(len(r.rungs) for c in p.controllers for x in c.programs for r in x.routines)
 print(f"Project: {p.name} ({p.project_id})\nControllers: {len(p.controllers)}; tags: {tags}; routines: {routines}; rungs: {rungs}\nDeployments: {len(p.deployments)}; targets: {', '.join(x.target_platform for x in p.deployments) or 'none'}\nProduced/consumed tags: {sum(len(c.produced_tags) for c in p.controllers)}/{sum(len(c.consumed_tags) for c in p.controllers)}\nSCADA screens/alarms: {len(p.scada.screens)}/{len(p.scada.alarms)}\nValidation: {'ERRORS' if any(x['severity']=='ERROR' for x in ds) else 'valid'}")
 return 1 if any(x["severity"]=="ERROR" for x in ds) else 0
if __name__=="__main__": raise SystemExit(main())
