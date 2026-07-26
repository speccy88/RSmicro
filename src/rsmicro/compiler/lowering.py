import struct
from typing import Any
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
  if b: storage=str(dirs[(b.device_id,b.endpoint_id)]).upper()
  tags.append(IRTag(n,t.tag_id,t.name,str(t.data_type),storage,t.initial_value if t.initial_value is not None else t.preset,t.retentive))
 ins:list[IRInstruction]=[]; routines:list[dict[str,Any]]=[]; rungs:list[dict[str,Any]]=[]; states=0; branches=0
 def emit_control(name,path):
  op={'BRANCH_BEGIN':240,'BRANCH_LANE_BEGIN':241,'BRANCH_LANE_END':242,'BRANCH_END':243}[name]
  ins.append(IRInstruction(len(ins),f'__{name.lower()}_{len(ins)}',name,op,tuple(),None,path+'/'+name))
 def nodes(seq,path):
  nonlocal states,branches
  for node in seq:
   if isinstance(node,Branch):
    branches+=1
    branch_path=path+f'/branch/{branches}'
    emit_control('BRANCH_BEGIN',branch_path)
    for k,lane in enumerate(node.lanes):
     emit_control('BRANCH_LANE_BEGIN',branch_path+f'/lane/{k}')
     nodes(lane,branch_path+f'/lane/{k}')
     emit_control('BRANCH_LANE_END',branch_path+f'/lane/{k}')
    emit_control('BRANCH_END',branch_path)
   else:
    m=ALIASES.get(node.mnemonic.upper(),node.mnemonic.upper()); ops=[]
    for o in node.operands:
     if isinstance(o,TagOperand):
      t=controller.tags[[x.tag_id for x in controller.tags].index(o.tag_id)]; typ=str(t.data_type)
      if o.member: typ='DINT' if o.member.upper() in {'PRE','ACC'} else 'BOOL'
      ops.append(IROperand('tag',typ,tid[o.tag_id],o.member.upper() if o.member else None))
     else: ops.append(IROperand('literal','BOOL' if isinstance(o.value,bool) else 'DINT' if isinstance(o.value,int) else 'REAL',o.value))
    # ABI 2 makes ONS state an explicit BOOL storage operand.  Legacy
    # zero-operand projects get a deterministic compiler-generated hidden tag;
    # they are never silently interpreted using an anonymous runtime slot.
    if m=='ONS' and not ops:
     hidden_id=len(tags)
     tags.append(IRTag(hidden_id,f'__rsm_ons_storage_{node.instruction_id}',f'__rsm_ons_storage_{node.instruction_id}','BOOL','INTERNAL',False,False))
     ops.append(IROperand('tag','BOOL',hidden_id,None))
    slot=states if m in {'TON','CTU','CTD'} else None
    if slot is not None: states+=1
    ins.append(IRInstruction(len(ins),node.instruction_id,m,OPCODES[m],tuple(ops),slot,path+'/'+node.instruction_id))
 for p in controller.programs:
  for r in p.routines:
   rid=len(routines); routines.append({'id':rid,'uuid':r.routine_id,'name':r.name})
   for rung in r.rungs:
    rg=len(rungs); start=len(ins); nodes(rung.nodes,f'{p.program_id}/{r.routine_id}/{rung.rung_id}'); rungs.append({'id':rg,'uuid':rung.rung_id,'routine_id':rid,'start':start,'count':len(ins)-start})
 produced=tuple(sorted((route.to_dict() for route in controller.produced_tags),key=lambda route:route['produced_tag_id']))
 consumed=tuple(sorted((route.to_dict() for route in controller.consumed_tags),key=lambda route:route['consumed_tag_id']))
 return IRProgram(PROFILE_ID,INSTRUCTION_ABI,controller.controller_id,tuple(tags),tuple(ins),tuple(routines),tuple(rungs),branches,produced,consumed)
