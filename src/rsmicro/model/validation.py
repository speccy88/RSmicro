from __future__ import annotations
from uuid import UUID
from rsmicro.diagnostics import Diagnostic,Severity
from .logic import Branch,Instruction
from .tags import TIMER_MEMBERS,COUNTER_MEMBERS,TagType

def validate_project(p, source_file=None):
 d=[]
 def add(sev,code,msg,path,**kw): d.append(Diagnostic(sev,code,msg,source_file,path,project_id=getattr(p,"project_id",None),**kw))
 if p.format!="rsmicro-project": add(Severity.ERROR,"FORMAT_UNSUPPORTED","Unsupported project format","/format")
 if p.format_version!=1: add(Severity.ERROR,"FORMAT_VERSION_UNSUPPORTED","Unsupported format version","/format_version")
 seen=set()
 def uid(v,path,ctx={}):
  try: UUID(v)
  except Exception: add(Severity.ERROR,"UUID_INVALID",f"Invalid UUID: {v}",path,**ctx); return
  if v in seen: add(Severity.ERROR,"UUID_DUPLICATE",f"Duplicate UUID: {v}",path,**ctx)
  seen.add(v)
 uid(p.project_id,"/project_id")
 controller_ids={c.controller_id for c in p.controllers}
 for ci,c in enumerate(p.controllers):
  ctx={"controller_id":c.controller_id}; uid(c.controller_id,f"/controllers/{ci}/controller_id")
  tags={t.tag_id:t for t in c.tags}; names=set()
  for ti,t in enumerate(c.tags):
   uid(t.tag_id,f"/controllers/{ci}/tags/{ti}/tag_id",ctx)
   if not t.name or t.name in names: add(Severity.ERROR,"TAG_NAME_DUPLICATE","Empty or duplicate tag name",f"/controllers/{ci}/tags/{ti}/name",**ctx)
   names.add(t.name)
   if t.data_type in {TagType.TIMER,TagType.COUNTER} and (t.preset is None or t.preset<0): add(Severity.ERROR,"TAG_PRESET_INVALID","Composite tag preset must be nonnegative",f"/controllers/{ci}/tags/{ti}/preset",**ctx)
   if t.data_type==TagType.BOOL and t.initial_value is not None and type(t.initial_value) is not bool: add(Severity.ERROR,"TAG_INITIAL_INVALID","BOOL initial value must be boolean",f"/controllers/{ci}/tags/{ti}/initial_value",**ctx)
  def nodes(ns,path):
   for ni,n in enumerate(ns):
    np=f"{path}/{ni}"
    if isinstance(n,Branch):
     if len(n.lanes)<2: add(Severity.ERROR,"BRANCH_INVALID","Branch requires at least two lanes",np,**ctx)
     for li,lane in enumerate(n.lanes):
      if not lane: add(Severity.ERROR,"BRANCH_LANE_EMPTY","Branch lane cannot be empty",f"{np}/lanes/{li}",**ctx)
      nodes(lane,f"{np}/lanes/{li}")
    else:
     uid(n.instruction_id,np+"/instruction_id",ctx)
     for oi,o in enumerate(n.operands):
      if hasattr(o,"tag_id"):
       if o.tag_id not in tags: add(Severity.ERROR,"TAG_REFERENCE_MISSING","Instruction references a missing tag",f"{np}/operands/{oi}",instruction_id=n.instruction_id,**ctx)
       elif o.member:
        allowed=TIMER_MEMBERS if tags[o.tag_id].data_type==TagType.TIMER else COUNTER_MEMBERS if tags[o.tag_id].data_type==TagType.COUNTER else set()
        if o.member not in allowed: add(Severity.ERROR,"TAG_MEMBER_INVALID",f"Invalid member {o.member}",f"{np}/operands/{oi}/member",instruction_id=n.instruction_id,**ctx)
  for pi,pr in enumerate(c.programs):
   uid(pr.program_id,f"/controllers/{ci}/programs/{pi}/program_id",ctx)
   for ri,ro in enumerate(pr.routines):
    uid(ro.routine_id,f"/controllers/{ci}/programs/{pi}/routines/{ri}/routine_id",ctx)
    for gi,ru in enumerate(ro.rungs): uid(ru.rung_id,f"/controllers/{ci}/programs/{pi}/routines/{ri}/rungs/{gi}/rung_id",ctx); nodes(ru.nodes,f"/controllers/{ci}/programs/{pi}/routines/{ri}/rungs/{gi}/nodes")
 for di,x in enumerate(p.deployments):
  uid(x.deployment_id,f"/deployments/{di}/deployment_id")
  if x.controller_id not in controller_ids: add(Severity.ERROR,"CONTROLLER_REFERENCE_MISSING","Deployment controller does not exist",f"/deployments/{di}/controller_id")
  eps={(v.device_id,e.endpoint_id):e for v in x.devices for e in v.endpoints}; bound=set()
  ctrl=next((c for c in p.controllers if c.controller_id==x.controller_id),None); tids={t.tag_id for t in ctrl.tags} if ctrl else set()
  for bi,b in enumerate(x.bindings):
   if b.tag_id not in tids or (b.device_id,b.endpoint_id) not in eps: add(Severity.ERROR,"DEPLOYMENT_BINDING_INVALID","Binding references a missing tag or endpoint",f"/deployments/{di}/bindings/{bi}")
   if b.tag_id in bound: add(Severity.ERROR,"DEPLOYMENT_BINDING_DUPLICATE","Tag has multiple bindings",f"/deployments/{di}/bindings/{bi}")
   bound.add(b.tag_id)
   e=eps.get((b.device_id,b.endpoint_id))
   if e and e.direction=="output" and e.safe_value is None: add(Severity.WARNING,"OUTPUT_SAFE_STATE_MISSING","Hardware output has no safe state",f"/deployments/{di}/devices")
 return d
