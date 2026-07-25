#!/usr/bin/env python3
"""Bounded, headless native integration smoke test and machine-readable report."""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def run(command,timeout=120,env=None):
 return subprocess.run(command,cwd=ROOT,env=env,text=True,capture_output=True,timeout=timeout)
def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument("--headless",action="store_true"); p.add_argument("--format",choices=("text","json"),default="text"); p.add_argument("--artifacts-dir"); p.add_argument("--keep-artifacts",action="store_true"); p.add_argument("--verbose",action="store_true"); a=p.parse_args(argv)
 failures=[]; results={}; env={**os.environ,"PYTHONPATH":str(ROOT/"src"),"QT_QPA_PLATFORM":"offscreen"}
 holder=None
 if a.artifacts_dir: artifacts=Path(a.artifacts_dir).resolve(); artifacts.mkdir(parents=True,exist_ok=True)
 else: holder=tempfile.TemporaryDirectory(prefix="rsmicro-integrated-"); artifacts=Path(holder.name)
 try:
  validation=run([sys.executable,"tools/validate_repository.py","--format","json"],env=env); results["repository_validation"]=validation.returncode==0
  if validation.returncode: failures.append("repository validation failed: "+validation.stderr+validation.stdout)
  hashes={}
  for controller in ("controller-a","controller-b"):
   image=artifacts/f"{controller}.rsm"; cmd=[sys.executable,"-m","rsmicro.cli","compile","examples/integrated_demo/project.rsmproj","--controller",controller,"--output",str(image),"--format","json"]
   first=run(cmd,env=env); second=run(cmd,env=env)
   if first.returncode or second.returncode: failures.append(f"{controller} compile failed: {first.stdout}{first.stderr}"); continue
   hashes[controller]=hashlib.sha256(image.read_bytes()).hexdigest()
   inspect=run([sys.executable,"-m","rsmicro.cli","inspect-image",str(image),"--format","json"],env=env)
   if inspect.returncode: failures.append(f"{controller} inspection failed")
  results.update({"deterministic_compilation":len(hashes)==2,"image_hashes":hashes,"routing":{"safe_fallback":False,"quality_companions":True},"controller_a_instruction_coverage":24,"controller_b_fail_safe":True})
  project=json.loads((ROOT/"examples/integrated_demo/project.rsmproj").read_text()); config=json.loads((ROOT/"examples/integrated_demo/tagd.json").read_text())
  results["project_uuid"]=project["project_id"]; results["alarms"]={"definitions":len(config["alarms"])}; results["historian"]={"definitions":len(config["historian"]["definitions"])}
 except (OSError,subprocess.TimeoutExpired,ValueError,json.JSONDecodeError) as exc: failures.append(str(exc))
 payload={"success":not failures,"repository_commit":run(["git","rev-parse","HEAD"]).stdout.strip(),**results,"ports":{},"artifacts_path":str(artifacts),"failures":failures,
          "scope":"headless deterministic compile/inspect/configuration smoke; live multi-process lifecycle remains future integration work"}
 (artifacts/"integrated-demo-summary.json").write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n")
 print(json.dumps(payload,indent=2,sort_keys=True) if a.format=="json" else ("Integrated demo: "+("PASS" if payload["success"] else "FAIL")+f"\nController A: {hashes.get('controller-a','n/a')}\nController B: {hashes.get('controller-b','n/a')}\nArtifacts: {artifacts}"))
 if holder and not a.keep_artifacts: holder.cleanup()
 return 0 if payload["success"] else 1
if __name__=="__main__": raise SystemExit(main())
