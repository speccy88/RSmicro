from __future__ import annotations
import argparse,json,sys
from pathlib import Path
from dataclasses import asdict
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
 n=sp.add_parser("native"); ns=n.add_subparsers(dest="native_command",required=True)
 ni=ns.add_parser("info"); ni.add_argument("--library"); ni.add_argument("--format",choices=["text","json"],default="text")
 nb=ns.add_parser("build"); nb.add_argument("--build-dir",default="build"); nb.add_argument("--clean",action="store_true"); g=nb.add_mutually_exclusive_group(); g.add_argument("--debug",action="store_true"); g.add_argument("--release",action="store_true"); nb.add_argument("--sanitize",action="store_true")
 rn=sp.add_parser("run-native"); rn.add_argument("project_or_image"); rn.add_argument("--controller"); rn.add_argument("--deployment"); rn.add_argument("--library"); rn.add_argument("--scan-period-ms",type=float,default=10); rn.add_argument("--mode",choices=["program","run","test"],default="program"); rn.add_argument("--manual",action="store_true"); rn.add_argument("--duration",type=float); rn.add_argument("--scenario"); rn.add_argument("--interactive",action="store_true"); rn.add_argument("--format",choices=["text","json"],default="text"); rn.add_argument("--show-tags",action="store_true"); rn.add_argument("--show-diagnostics",action="store_true")
 pr=sp.add_parser("profile"); prs=pr.add_subparsers(dest="profile_command",required=True)
 for command in ("show","instructions","instruction"):
  q=prs.add_parser(command); q.add_argument("profile");
  if command=="instruction": q.add_argument("mnemonic")
 sc=sp.add_parser("scada",help="query a running local tag broker"); scs=sc.add_subparsers(dest="scada_command",required=True)
 for command in ("info","controllers","tags","read","write","force","unforce","clear-forces","monitor","alarms","acknowledge","history","routes","diagnostics"):
  q=scs.add_parser(command); q.add_argument("arguments",nargs="*"); q.add_argument("--host",default="127.0.0.1"); q.add_argument("--port",type=int,default=7590); q.add_argument("--timeout",type=float,default=5); q.add_argument("--format",choices=("text","json"),default="text"); q.add_argument("--role",choices=("viewer","operator","engineering"),default="viewer")
 hi=sp.add_parser("history",help="inspect a SQLite historian"); his=hi.add_subparsers(dest="history_command",required=True)
 for command in ("info","tags","query","prune","verify","migrate"):
  q=his.add_parser(command); q.add_argument("tag",nargs="?"); q.add_argument("--database",required=True); q.add_argument("--from",dest="start"); q.add_argument("--to",dest="end"); q.add_argument("--before"); q.add_argument("--format",choices=("text","json"),default="text")
 al=sp.add_parser("alarms",help="operate alarms through the broker"); als=al.add_subparsers(dest="alarms_command",required=True)
 for command in ("list","active","acknowledge","history"):
  q=als.add_parser(command); q.add_argument("alarm_id",nargs="?"); q.add_argument("--host",default="127.0.0.1"); q.add_argument("--port",type=int,default=7590); q.add_argument("--user",default="cli"); q.add_argument("--comment",default="")
 a=ap.parse_args(argv)
 if a.command=="history":
  from .scada.historian import Historian
  try:
   h=Historian(a.database).open()
   if a.history_command in ("info","verify","migrate"): payload={"database":str(h.path),"schema_version":h._conn.execute("PRAGMA user_version").fetchone()[0],"journal_mode":h._conn.execute("PRAGMA journal_mode").fetchone()[0],"integrity":h._conn.execute("PRAGMA quick_check").fetchone()[0]}
   elif a.history_command=="tags": payload=[dict(zip(("tag_uuid","controller_uuid","qualified_name","data_type"),x)) for x in h._conn.execute("SELECT tag_uuid,controller_uuid,qualified_name,data_type FROM tags")]
   elif a.history_command=="query": payload=h.query(a.tag,a.start,a.end)
   else: payload={"pruned":h.prune(a.before)}
   h._conn.close(); print(json.dumps(payload,indent=2,default=str)); return 0
  except Exception as e: print(f"error: {e}",file=sys.stderr); return 1
 if a.command in ("scada","alarms"):
  from .scada.client import ScadaClient
  async def invoke():
   role=getattr(a,"role","operator").upper()
   async with ScadaClient(a.host,a.port,getattr(a,"timeout",5),role) as client:
    cmd=a.scada_command if a.command=="scada" else a.alarms_command
    if cmd=="info":return await client.service_info()
    if cmd=="controllers":return await client.controllers()
    if cmd=="tags":return await client.tags()
    if cmd=="routes":return await client.routes()
    if cmd=="diagnostics":return await client.diagnostics()
    if cmd in ("alarms","list","active"):return await client.alarms()
    if cmd=="read":return await client.read(a.arguments[0])
    if cmd=="write":return await client.write(a.arguments[0],json.loads(a.arguments[1]))
    if cmd=="force":return await client.force(a.arguments[0],json.loads(a.arguments[1]))
    if cmd=="unforce":return await client.unforce(a.arguments[0])
    if cmd=="acknowledge":return await client.acknowledge(a.alarm_id if a.command=="alarms" else a.arguments[0],getattr(a,"user","cli"),getattr(a,"comment",""))
    raise ValueError(f"{cmd} requires streaming or additional arguments")
  import asyncio
  try: print(json.dumps(asyncio.run(invoke()),indent=2)); return 0
  except Exception as e: print(f"error: {e}",file=sys.stderr); return 1
 if a.command=="native":
  if a.native_command=="build":
   from .native.build import build_native
   try: path=build_native(a.build_dir,a.clean,"Debug" if a.debug else "Release",a.sanitize)
   except Exception as e: print(f"error: {e}",file=sys.stderr); return 1
   print(path); return 0
  from .native import NativeBinding
  try: b=NativeBinding(a.library); payload={"library_path":b.path,"search_locations":list(b.search.candidates),"runtime_abi":{"major":b.lib.rsm_runtime_abi_major(),"minor":b.lib.rsm_runtime_abi_minor()},"instruction_abi":b.lib.rsm_instruction_abi(),"image_format":{"major":b.lib.rsm_image_format_major(),"minor":b.lib.rsm_image_format_minor()},"profile":"RSM-LOGIX-CORE-1" if b.lib.rsm_profile_id()==1 else b.lib.rsm_profile_id()}
  except Exception as e: print(json.dumps({"error":str(e)}) if a.format=="json" else f"error: {e}",file=sys.stderr); return 1
  print(json.dumps(payload,indent=2,sort_keys=True) if a.format=="json" else "\n".join(f"{k}: {v}" for k,v in payload.items())); return 0
 if a.command=="run-native":
  from .native import NativeRuntime,NativeSimulator,RuntimeMode
  try:
   path=Path(a.project_or_image)
   if path.suffix==".rsm": sim=NativeSimulator(NativeRuntime(a.library).load_image(path),a.scan_period_ms)
   else:
    if not a.controller: raise ValueError("--controller is required for a project")
    sim=NativeSimulator.from_project(path,a.controller,a.deployment,a.library,a.scan_period_ms)
   sim.set_mode({"program":RuntimeMode.PROGRAM,"run":RuntimeMode.RUN,"test":RuntimeMode.TEST}[a.mode])
   scenario_results=[]
   if a.scenario:
    for step in json.loads(Path(a.scenario).read_text()).get("steps",[]):
     op=step["operation"]
     if op=="mode": sim.set_mode(RuntimeMode[step["value"].upper()])
     elif op=="advance_time_us": sim.hal.advance_time_us(step["value"])
     elif op=="scan":
      for _ in range(step.get("count",1)): sim.scan()
     elif op=="write": sim.runtime.write_tag(step["tag"],step["value"])
     elif op=="force": sim.runtime.force_tag(step["tag"],step["value"])
     elif op=="unforce": sim.runtime.clear_force(step["tag"])
     elif op=="read": scenario_results.append({"tag":step["tag"],"value":sim.runtime.read_tag(step["tag"]).value})
   if a.duration:
    sim.start(); __import__('time').sleep(a.duration); sim.stop()
   snap=sim.runtime.snapshot(); payload={"state":sim.state.value,"mode":sim.runtime.mode.name,"program_hash":snap.program_hash,"scan_count":snap.scan_count,"results":scenario_results,"diagnostics":snap.diagnostics.to_dict(),"fault":None if not snap.last_fault else asdict(snap.last_fault)}
   print(json.dumps(payload,indent=2,sort_keys=True) if a.format=="json" else "\n".join(f"{k}: {v}" for k,v in payload.items())); sim.close(); return 0
  except Exception as e: print(json.dumps({"error":str(e)}) if a.format=="json" else f"error: {e}",file=sys.stderr); return 1
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
