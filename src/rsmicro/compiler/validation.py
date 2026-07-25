import math
from .diagnostics import CompilerDiagnostic as D
from .generated_opcodes import OPCODES,ALIASES
from rsmicro.model.logic import Branch,Instruction,TagOperand,LiteralOperand
MEMBERS={'TIMER':{'PRE','ACC','EN','TT','DN'},'COUNTER':{'PRE','ACC','CU','CD','DN','OV','UN'}}
OWNED={'TIMER':{'ACC','EN','TT','DN'},'COUNTER':{'ACC','CU','CD','DN','OV','UN'}}
def walk(nodes):
 for n in nodes:
  if isinstance(n,Branch):
   for lane in n.lanes: yield from walk(lane)
  else: yield n
def validate_controller(c):
 ds=[]; tags={t.tag_id:t for t in c.tags}; writes={}; seen=set()
 for p in c.programs:
  for r in p.routines:
   for rung in r.rungs:
    for i in walk(rung.nodes):
     path=f'{p.name}/{r.name}/{rung.rung_id}/{i.instruction_id}'
     if i.instruction_id in seen: ds.append(D('ERROR','RSM-E113','duplicate instruction UUID',path))
     seen.add(i.instruction_id); m=i.mnemonic.upper()
     if m in ALIASES: ds.append(D('WARNING','RSM-W204',f'deprecated mnemonic alias {m} normalized to {ALIASES[m]}',path)); m=ALIASES[m]
     if m not in OPCODES: ds.append(D('ERROR','RSM-E101',f'unsupported instruction {m}',path)); continue
     from .profile import load_instruction
     spec=load_instruction(m)
     if len(i.operands)!=len(spec['operands']): ds.append(D('ERROR','RSM-E102',f'{m} expects {len(spec["operands"])} operands, got {len(i.operands)}',path)); continue
     for idx,(o,rule) in enumerate(zip(i.operands,spec['operands'])):
      if isinstance(o,TagOperand):
       t=tags.get(o.tag_id)
       if not t: ds.append(D('ERROR','RSM-E103',f'missing tag {o.tag_id}',path)); continue
       typ=str(t.data_type); member=o.member.upper() if o.member else None
       if member:
        if typ not in MEMBERS or member not in MEMBERS[typ]: ds.append(D('ERROR','RSM-E104',f'invalid member {o.member} for {typ}',path)); continue
        typ='DINT' if member in {'PRE','ACC'} else 'BOOL'
       if typ not in rule['types']: ds.append(D('ERROR','RSM-E105',f'operand {idx+1}: {typ} not in {rule["types"]}',path))
       if rule['writable'] and (not t.writable or (member and member in OWNED.get(str(t.data_type),set()))): ds.append(D('ERROR','RSM-E106','destination is not writable',path))
       if rule['writable']: writes.setdefault((t.tag_id,member),[]).append(path)
      else:
       v=o.value
       if not rule['literal']: ds.append(D('ERROR','RSM-E105','literal not permitted',path))
       if isinstance(v,int) and not isinstance(v,bool) and not -2147483648<=v<=2147483647: ds.append(D('ERROR','RSM-E116','DINT literal out of range',path))
       if isinstance(v,float) and not math.isfinite(v): ds.append(D('ERROR','RSM-E115','non-finite REAL literal',path))
 for dest,paths in writes.items():
  if len(paths)>1: ds.append(D('WARNING','RSM-W200',f'multiple destructive writes to {dest[0]}',paths[-1]))
 return ds
