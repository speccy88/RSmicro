#!/usr/bin/env python3
"""Static, deterministic release-readiness checks for the RSmicro repository."""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument("--format",choices=("text","json"),default="text"); a=p.parse_args(argv)
 errors=[]; warnings=[]; checks=[]
 def check(name,condition,detail=""):
  checks.append({"name":name,"passed":bool(condition),"detail":detail})
  if not condition: errors.append(f"{name}: {detail}")
 for path in ("src/rsmicro","runtime/core","runtime/node","protocol","profiles","schemas","examples/integrated_demo"):
  check(f"required:{path}",(ROOT/path).exists(),"required path is missing")
 text=(ROOT/"pyproject.toml").read_text();
 for entry in ("rsmicro =","rsmicro-tagd =","plc-ascii =","plc-runtime ="):
  check(f"entry-point:{entry[:-2]}",entry in text,"entry point is missing")
 cmake="\n".join(x.read_text(errors="replace") for x in ROOT.rglob("CMakeLists.txt"))
 for target in ("rsmcore","rsmnode","rsmlink") : check(f"cmake-target:{target}",target in cmake,"target is missing")
 tracked=subprocess.run(["git","ls-files"],cwd=ROOT,text=True,capture_output=True,check=True).stdout.splitlines()
 check("no-tracked-build",not any(x.startswith(("build/","build-")) for x in tracked),"tracked build output")
 check("no-tracked-bytecode",not any(x.endswith((".pyc",".pyo")) for x in tracked),"tracked Python bytecode")
 source=[x for x in tracked if x.endswith((".py",".c",".h",".json",".toml",".yml",".yaml",".md"))]
 cloud=[]; external=[]
 for rel in source:
  value=(ROOT/rel).read_text(errors="replace")
  if "/workspace/" in value or "/root/" in value: cloud.append(rel)
  if rel.startswith(("src/","runtime/","protocol/","examples/")) and re.search(r'(?<![\w.])0\.0\.0\.0(?![\w.])',value): external.append(rel)
 check("no-cloud-paths",not cloud,", ".join(cloud))
 check("loopback-defaults",not external,"external bind in production/example source: "+", ".join(external))
 screens=list((ROOT/"examples/integrated_demo/screens").glob("*.json"))
 check("screen-data-only",all(not json.loads(x.read_text()).get("executable_code",True) for x in screens),"screen permits executable code")
 for tool in ("generate_instruction_registry.py","generate_c_conformance_fixtures.py","generate_rsm_link_registry.py"):
  result=subprocess.run([sys.executable,str(ROOT/"tools"/tool),"--check"],cwd=ROOT,capture_output=True,text=True)
  check(f"generated:{tool}",result.returncode==0,(result.stdout+result.stderr).strip())
 env={**__import__('os').environ,"PYTHONPATH":str(ROOT/"src")}
 result=subprocess.run([sys.executable,"-m","rsmicro.cli","validate",str(ROOT/"examples/integrated_demo/project.rsmproj")],cwd=ROOT,env=env,capture_output=True,text=True)
 check("integrated-project-valid",result.returncode==0,(result.stdout+result.stderr).strip())
 result_payload={"success":not errors,"checks":checks,"errors":errors,"warnings":warnings}
 if a.format=="json": print(json.dumps(result_payload,indent=2))
 else:
  for x in checks: print(("PASS" if x["passed"] else "FAIL")+" "+x["name"]+(f": {x['detail']}" if x['detail'] and not x["passed"] else ""))
  print(f"\n{len(checks)-len(errors)} passed, {len(errors)} errors, {len(warnings)} warnings")
 return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
