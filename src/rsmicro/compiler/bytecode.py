import struct
TYPE={'BOOL':1,'DINT':2,'REAL':3,'TIMER':4,'COUNTER':5}
def encode_instruction_stream(ir):
 out=bytearray()
 for i in ir.instructions:
  out += struct.pack('<BBHI',i.opcode,len(i.operands),0,i.id)
  out += struct.pack('<i',-1 if i.state_slot is None else i.state_slot)
  for o in i.operands:
   kind=1 if o.kind=='tag' else 2; member={'PRE':1,'ACC':2,'EN':3,'TT':4,'DN':5,'CU':6,'CD':7,'OV':8,'UN':9}.get(o.member,0)
   out += struct.pack('<BBBB',kind,TYPE[o.type],member,0)
   if o.kind=='tag': out += struct.pack('<I',o.value)
   elif o.type=='BOOL': out += struct.pack('<I',1 if o.value else 0)
   elif o.type=='DINT': out += struct.pack('<i',o.value)
   else: out += struct.pack('<f',o.value)
 return bytes(out)
