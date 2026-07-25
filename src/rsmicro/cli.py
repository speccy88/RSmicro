from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from .diagnostics import Severity
from .migration import migrate_legacy
from .model import load_project,validate_project
from .schemas import validate_schema
from .compiler import compile_project,CompileOptions,inspect_image
from .compiler.profile import load_profile,load_instruction

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
 c=sp.add_parser("compile"); c.add_argument("project"); c.add_argument("--controller",required=True); c.add_argument("--output",required=True); c.add_argument("--deployment"); c.add_argument("--profile",default="RSM-LOGIX-CORE-1"); c.add_argument("--manifest"); c.add_argument("--debug-map"); c.add_argument("--warnings-as-errors",action="store_true"); c.add_argument("--strip-debug",action="store_true"); c.add_argument("--format",choices=["text","json"],default="text")
 i=sp.add_parser("inspect-image"); i.add_argument("image"); i.add_argument("--format",choices=["text","json"],default="text")
 pr=sp.add_parser("profile"); prs=pr.add_subparsers(dest="profile_command",required=True)
 for command in ("show","instructions","instruction"):
  q=prs.add_parser(command); q.add_argument("profile");
  if command=="instruction": q.add_argument("mnemonic")
 a=ap.parse_args(argv)
 if a.command=="profile":
  try: p=load_profile(a.profile)
  except ValueError as e: print(str(e),file=sys.stderr); return 1
  if a.profile_command=="show": print(json.dumps(p,indent=2,sort_keys=True))
  elif a.profile_command=="instructions": print("\n".join(f"{x['mnemonic']}\t{x['opcode']}" for x in p['instructions']))
  else:
   try: print(json.dumps(load_instruction(a.mnemonic.upper()),indent=2,sort_keys=True))
   except FileNotFoundError: print("unsupported instruction",file=sys.stderr); return 1
  return 0
 if a.command=="inspect-image":
  try: info=inspect_image(Path(a.image).read_bytes())
  except (OSError,ValueError) as e: print(f"error: {e}",file=sys.stderr); return 1
  print(json.dumps(info,indent=2,sort_keys=True) if a.format=="json" else "\n".join(f"{k}: {v}" for k,v in info.items()))
  return 0
 if a.command=="compile":
  p,base=diagnostics(a.project)
  if p is None or any(x['severity']=='ERROR' for x in base):
   print(json.dumps(base,indent=2) if a.format=='json' else "\n".join(f"{x['severity']} {x['code']}: {x['message']}" for x in base)); return 1
  result=compile_project(p,a.controller,a.profile,a.deployment,CompileOptions(a.warnings_as_errors,a.strip_debug))
  payload=[x.to_dict() for x in result.diagnostics]
  if not result.success:
   print(json.dumps(payload,indent=2) if a.format=='json' else "\n".join(f"{x['severity']} {x['code']}: {x['message']}" for x in payload)); return 1
  out=Path(a.output); mp=Path(a.manifest or str(out)+'.manifest.json'); dp=Path(a.debug_map or str(out)+'.map.json')
  import os,tempfile
  def atomic(path,data,binary=False):
   path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=path.parent,prefix='.'+path.name+'.'); os.close(fd)
   try: Path(tmp).write_bytes(data) if binary else Path(tmp).write_text(data,encoding='utf-8'); os.replace(tmp,path)
   finally:
    if Path(tmp).exists(): Path(tmp).unlink()
  atomic(out,result.image_bytes,True); atomic(mp,json.dumps(result.manifest,indent=2,sort_keys=True)+'\n'); atomic(dp,json.dumps(result.debug_map,indent=2,sort_keys=True)+'\n')
  print(json.dumps({'success':True,'image':str(out),'manifest':str(mp),'debug_map':str(dp),'hashes':result.hashes,'diagnostics':payload},indent=2) if a.format=='json' else f"Compiled {out} ({result.hashes['sha256']})")
  return 0
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
