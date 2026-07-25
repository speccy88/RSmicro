import json,struct,zlib,hashlib,uuid
from .bytecode import encode_instruction_stream
MAGIC=b'RSM1'; VERSION=(1,0); HEADER_FMT='<4sBBHIIHH16s32sI'; DESC_FMT='<HHIIII'; HEADER_SIZE=struct.calcsize(HEADER_FMT); DESC_SIZE=struct.calcsize(DESC_FMT)
SECTIONS={'TAG_TABLE':1,'INITIAL_VALUES':2,'TIMER_LAYOUT':3,'COUNTER_LAYOUT':4,'TASK_TABLE':5,'ROUTINE_TABLE':6,'RUNG_TABLE':7,'INSTRUCTION_STREAM':8,'STATE_LAYOUT':9,'PRODUCED_TAGS':10,'CONSUMED_TAGS':11,'DEBUG_MAP':12,'STRING_TABLE':13,'MEMORY_ESTIMATES':14}
def canonical(x): return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def memory(ir):
 counts={t:sum(x.type==t for x in ir.tags) for t in ['BOOL','DINT','REAL','TIMER','COUNTER']}; scalar=counts['BOOL']+4*(counts['DINT']+counts['REAL']); total=64+scalar+16*counts['TIMER']+20*counts['COUNTER']+len(ir.tags)*2+len([x for x in ir.instructions if x.state_slot is not None])*16+ir.branches*8
 return {'runtime_structure_overhead':64,'scalar_tags':scalar,'timers':16*counts['TIMER'],'counters':20*counts['COUNTER'],'force_overlays':len(ir.tags)*2,'instruction_state':len([x for x in ir.instructions if x.state_slot is not None])*16,'branch_state':ir.branches*8,'input_image':counts['BOOL'],'output_image':counts['BOOL'],'command_staging':64,'change_tracking':len(ir.tags)*4,'runtime_arena_bytes':total+64+len(ir.tags)*4}
def debug(ir): return {'tags':[{'runtime_id':t.id,'uuid':t.uuid,'name':t.name,'type':t.type} for t in ir.tags],'routines':list(ir.routines),'rungs':list(ir.rungs),'instructions':[{'runtime_id':i.id,'uuid':i.uuid,'mnemonic':i.mnemonic,'opcode':i.opcode,'source_path':i.path,'state_slot':i.state_slot} for i in ir.instructions]}
def build(ir,strip_debug=False):
 dbg={} if strip_debug else debug(ir); mem=memory(ir)
 data={'TAG_TABLE':canonical([t.__dict__ if hasattr(t,'__dict__') else {'id':t.id,'uuid':t.uuid,'name':t.name,'type':t.type,'storage':t.storage,'retentive':t.retentive} for t in ir.tags]),'INITIAL_VALUES':canonical([t.initial for t in ir.tags]),'TIMER_LAYOUT':canonical([t.id for t in ir.tags if t.type=='TIMER']),'COUNTER_LAYOUT':canonical([t.id for t in ir.tags if t.type=='COUNTER']),'TASK_TABLE':canonical([{'id':0}]),'ROUTINE_TABLE':canonical(ir.routines),'RUNG_TABLE':canonical(ir.rungs),'INSTRUCTION_STREAM':encode_instruction_stream(ir),'STATE_LAYOUT':canonical([{'slot':i.state_slot,'instruction_id':i.id} for i in ir.instructions if i.state_slot is not None]),'PRODUCED_TAGS':b'[]','CONSUMED_TAGS':b'[]','DEBUG_MAP':canonical(dbg),'STRING_TABLE':canonical(sorted({t.name for t in ir.tags})),'MEMORY_ESTIMATES':canonical(mem)}
 names=list(SECTIONS); count=len(names); offset=HEADER_SIZE+count*DESC_SIZE; desc=[]; payload=bytearray()
 for n in names:
  b=data[n]; desc.append(struct.pack(DESC_FMT,SECTIONS[n],0,offset,len(b),0,0)); payload+=b; offset+=len(b)
 total=offset; content_hash=hashlib.sha256(b''.join(data[n] for n in names)).digest(); uid=uuid.UUID(ir.controller_uuid).bytes
 header=struct.pack(HEADER_FMT,MAGIC,*VERSION,HEADER_SIZE,total,1,ir.abi,count,uid,content_hash,0); raw=bytearray(header+b''.join(desc)+payload); crc=zlib.crc32(raw)&0xffffffff; struct.pack_into('<I',raw,HEADER_SIZE-4,crc); return bytes(raw),dbg,mem,crc
