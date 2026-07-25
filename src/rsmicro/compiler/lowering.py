import struct
from .ir import *
from .generated_opcodes import OPCODES,ALIASES,PROFILE_ID,INSTRUCTION_ABI
from rsmicro.model.logic import Branch,TagOperand

def lower(controller,deployment=None):
 bound={b.tag_id:b for b in deployment.bindings} if deployment else {}
 dirs={}
 if deployment:
  for d in deployment.devices:
   for e in d.endpoints: dirs[(d.device_id,e.endpoint_id)]=e.direction
 tags=[]; tid={}
 for n,t in enumerate(sorted(controller.tags,key=lambda x:x.tag_id)):
  tid[t.tag_id]=n; b=bound.get(t.tag_id); storage='INTERNAL'
  if b: storage=str(dirs.get((b.device_id,b.endpoint_id),'internal')).upper()
  tags.append(IRTag(n,t.tag_id,t.name,str(t.data_type),storage,t.initial_value if t.initial_value is not None else t.preset,t.retentive))
 ins=[]; routines=[]; rungs=[]; states=0; branches=0
 def nodes(seq,path):
  nonlocal states,branches
  for node in seq:
   if isinstance(node,Branch):
    branches+=1
    for k,lane in enumerate(node.lanes): nodes(lane,path+f'/branch/{branches}/lane/{k}')
   else:
    m=ALIASES.get(node.mnemonic.upper(),node.mnemonic.upper()); ops=[]
    for o in node.operands:
     if isinstance(o,TagOperand):
      t=controller.tags[[x.tag_id for x in controller.tags].index(o.tag_id)]; typ=str(t.data_type)
      if o.member: typ='DINT' if o.member.upper() in {'PRE','ACC'} else 'BOOL'
      ops.append(IROperand('tag',typ,tid[o.tag_id],o.member.upper() if o.member else None))
     else: ops.append(IROperand('literal','BOOL' if isinstance(o.value,bool) else 'DINT' if isinstance(o.value,int) else 'REAL',o.value))
    slot=states if m in {'ONS','TON','CTU','CTD'} else None
    if slot is not None: states+=1
    ins.append(IRInstruction(len(ins),node.instruction_id,m,OPCODES[m],tuple(ops),slot,path+'/'+node.instruction_id))
 for p in controller.programs:
  for r in p.routines:
   rid=len(routines); routines.append({'id':rid,'uuid':r.routine_id,'name':r.name})
   for rung in r.rungs:
    rg=len(rungs); start=len(ins); nodes(rung.nodes,f'{p.program_id}/{r.routine_id}/{rung.rung_id}'); rungs.append({'id':rg,'uuid':rung.rung_id,'routine_id':rid,'start':start,'count':len(ins)-start})
 return IRProgram(PROFILE_ID,INSTRUCTION_ABI,controller.controller_id,tuple(tags),tuple(ins),tuple(routines),tuple(rungs),branches)
