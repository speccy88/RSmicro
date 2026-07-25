from __future__ import annotations
import json
from pathlib import Path
from uuid import UUID,uuid5
from rsmicro.diagnostics import Severity
from rsmicro.model.controller import Controller
from rsmicro.model.deployment import Binding,Deployment,Device,Endpoint
from rsmicro.model.logic import Branch,Instruction,LiteralOperand,Program,Routine,Rung,TagOperand
from rsmicro.model.project import Project
from rsmicro.model.serialization import save_project
from rsmicro.model.tags import Tag,TagType
from rsmicro.model.validation import validate_project
from .report import MigrationReport
NS=UUID("db08420c-3773-5a8f-a17f-749cfdde75fc")
KNOWN={"XIC","XIO","CMP","EQ","GT","GTE","GE","LT","LE","NE","OTE","OTL","OTU","TON","CTU","CTD","MOV","CLR","ADD","ABS","MUL","DIV","NEG","SUB"}
def sid(root,path): return str(uuid5(NS,f"{root}:{path}"))
def migrate_legacy(source,output=None):
 src=Path(source); raw=src.read_bytes(); data=json.loads(raw); root=f"{src.name}:{data.get('name','project')}"; report=MigrationReport(str(src),str(output or "")); name=str(data.get("name") or src.stem)
 varsrc=list(data.get("variables",[])); inferred={}
 def scan(nodes):
  for n in nodes:
   if n.get("kind")=="branch":
    for lane in n.get("lanes",[]): scan(lane)
   else:
    vals=[n.get("tag")]+list(n.get("params",{}).values())
    for v in vals:
     if isinstance(v,str): inferred.setdefault(v.split(".",1)[0],"timer" if "." in v or n.get("op")=="TON" else "bool")
 for rung in data.get("rungs",[]): scan(rung.get("elements",rung.get("conditions",[])+rung.get("actions",[])))
 existing={v.get("tag") for v in varsrc}
 for n,t in inferred.items():
  if n not in existing: varsrc.append({"tag":n,"type":t,"preset":0} if t=="timer" else {"tag":n,"type":t,"initial":False}); report.warnings.append({"code":"TAG_INFERRED","message":f"Inferred undeclared tag {n}"})
 typ={"bool":TagType.BOOL,"int":TagType.DINT,"float":TagType.REAL,"timer":TagType.TIMER,"counter":TagType.COUNTER}; tags=[]; byname={}
 for i,v in enumerate(varsrc):
  tid=sid(root,f"controller/tag/{v['tag']}"); byname[v["tag"]]=tid; dt=typ.get(str(v.get("type","bool")).lower())
  if not dt: dt=TagType.BOOL; report.errors.append({"code":"TAG_TYPE_INVALID","message":f"Unsupported type {v.get('type')}"})
  tags.append(Tag(tid,str(v["tag"]),dt,initial_value=v.get("initial") if dt in {TagType.BOOL,TagType.DINT,TagType.REAL} else None,preset=int(v.get("preset",0)) if dt in {TagType.TIMER,TagType.COUNTER} else None))
 def operand(v):
  if isinstance(v,(bool,int,float)): return LiteralOperand(v)
  base,_,member=str(v).partition("."); return TagOperand(byname.get(base,sid(root,f"missing/{base}")),member.upper() or None)
 def node(n,path):
  if n.get("kind")=="branch": return Branch([[node(x,f"{path}/lane/{li}/{xi}") for xi,x in enumerate(lane)] for li,lane in enumerate(n.get("lanes",[]))])
  op=str(n.get("op","")).upper(); original=op
  if op=="GTE": op="GE"; report.aliases_normalized.append({"from":"GTE","to":"GE","path":path}); report.warnings.append({"code":"INSTRUCTION_ALIAS_NORMALIZED","message":"GTE normalized to GE"})
  if original not in KNOWN: report.errors.append({"code":"INSTRUCTION_UNSUPPORTED","message":f"Unsupported instruction {original}","path":path})
  vals=[]
  if n.get("tag") not in (None,""): vals.append(operand(n["tag"]))
  if n.get("arg") is not None: vals.append(LiteralOperand(n["arg"]))
  for k in ("left","right","source","dest"):
   if k in n.get("params",{}): vals.append(operand(n["params"][k]))
  return Instruction(sid(root,f"instruction/{path}"),op or "UNSUPPORTED",vals,{"legacy":{k:v for k,v in n.items() if k not in {"kind","op","tag","arg","params"}}})
 rungs=[]
 for i,r in enumerate(data.get("rungs",[])):
  ns=r.get("elements",r.get("conditions",[])+r.get("actions",[])); rungs.append(Rung(sid(root,f"rung/{i}"),[node(n,f"rung/{i}/node/{j}") for j,n in enumerate(ns)],str(r.get("comment","")),{"legacy_name":r.get("name","")}))
 cid=sid(root,"controller"); pid=sid(root,"program/0"); rid=sid(root,"routine/0")
 ctrl=Controller(cid,name,tags=tags,programs=[Program(pid,"MainProgram",[Routine(rid,"MainRoutine",rungs)])],cyclic_task={"name":"MainTask","program_order":[pid]})
 target=str(data.get("runtime_target","circuitpython")); depid=sid(root,"deployment"); deviceid=sid(root,"deployment/device/legacy-io"); endpoints=[]; bindings=[]
 for i,b in enumerate(data.get("bindings",[])):
  eid=f"endpoint-{i}"; direction=str(b.get("direction","input")); endpoints.append(Endpoint(eid,direction,"BOOL",b.get("address",""),direction=="input",direction=="output"))
  bindings.append(Binding(sid(root,f"binding/{i}"),byname.get(str(b.get("tag")),sid(root,f"missing/{b.get('tag')}")),deviceid,eid,{"legacy_direction":direction}))
 dep=Deployment(depid,f"{name} deployment",cid,target,devices=[Device(deviceid,"legacy-io",properties={},endpoints=endpoints)],bindings=bindings,metadata={"legacy_runtime_target":target})
 known_top={"name","runtime_target","rungs","variables","bindings"}; unknown=sorted(set(data)-known_top); report.unsupported_fields=unknown
 project=Project(sid(root,"project"),name,controllers=[ctrl],deployments=[dep],metadata={"migration":{"source_format":"plc-ascii-v1","unsupported_fields":unknown}})
 diagnostics=validate_project(project,str(src)); report.warnings.extend(x.to_dict() for x in diagnostics if x.severity==Severity.WARNING); report.errors.extend(x.to_dict() for x in diagnostics if x.severity==Severity.ERROR)
 report.objects_migrated={"controllers":1,"tags":len(tags),"rungs":len(rungs),"bindings":len(bindings)}; report.uuid_mapping_summary={"project":project.project_id,"controller":cid}; report.deployment_information={"target_platform":target,"bindings":len(bindings)}
 if output: save_project(project,output)
 return project,report
