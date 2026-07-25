from dataclasses import dataclass,asdict
import struct
@dataclass(frozen=True)
class Hello: client_name:str; protocol_major:int=1; protocol_minor:int=0; requested_features:int=0
@dataclass(frozen=True)
class Ack: original_message_type:int; status:str="OK"; completion_sequence:int=0; applied_scan_number:int|None=None
@dataclass(frozen=True)
class Error: original_message_type:int; error_code:int; identifier:str; recoverable:bool=False
def encode_message(message)->bytes:
 value=asdict(message) if hasattr(message,"__dataclass_fields__") else message
 out=bytearray(struct.pack("<H",len(value)))
 for key,val in sorted(value.items()):
  kb=key.encode(); out.extend(struct.pack("<B",len(kb))); out.extend(kb)
  if val is None: out.append(0)
  elif isinstance(val,bool): out.extend((1,int(val)))
  elif isinstance(val,int): out.append(2); out.extend(struct.pack("<q",val))
  elif isinstance(val,float): out.append(3); out.extend(struct.pack("<d",val))
  elif isinstance(val,str):
   b=val.encode(); out.append(4); out.extend(struct.pack("<H",len(b))); out.extend(b)
  elif isinstance(val,bytes): out.append(5); out.extend(struct.pack("<I",len(val))); out.extend(val)
  else: raise TypeError(f"unsupported wire value: {type(val).__name__}")
 return bytes(out)
def decode_message(payload:bytes)->dict:
 pos=0
 def take(n):
  nonlocal pos
  if pos+n>len(payload): raise ValueError("truncated message")
  b=payload[pos:pos+n]; pos+=n; return b
 count=struct.unpack("<H",take(2))[0]; result={}
 for _ in range(count):
  key=take(take(1)[0]).decode(); kind=take(1)[0]
  if kind==0: value=None
  elif kind==1:
   value=take(1)[0]
   if value>1: raise ValueError("invalid BOOL")
   value=bool(value)
  elif kind==2: value=struct.unpack("<q",take(8))[0]
  elif kind==3: value=struct.unpack("<d",take(8))[0]
  elif kind in (4,5):
   n=struct.unpack("<H" if kind==4 else "<I",take(2 if kind==4 else 4))[0]; value=take(n); value=value.decode() if kind==4 else value
  else: raise ValueError("unknown required field type")
  result[key]=value
 if pos!=len(payload): raise ValueError("trailing message bytes")
 return result
