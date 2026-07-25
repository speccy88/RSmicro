from __future__ import annotations
import ctypes as C, hashlib, json, threading, time
from dataclasses import asdict,dataclass
from enum import IntEnum
from pathlib import Path
from .abi import *
from .binding import NativeBinding
from .errors import NativeImageError,NativeTagError,RSmicroNativeError
from .values import BoolValue,DintValue,RealValue,TimerValue,CounterValue,normalize

class RuntimeMode(IntEnum): PROGRAM=0; RUN=1; TEST=2; FAULTED=3

class NativeSimulationHAL:
 def __init__(self,manual=True):
  self.manual=manual; self._time_us=0; self.inputs={}; self.outputs={}; self.safe_outputs={}; self.read_count=self.write_count=self.watchdog_count=0; self.fail_reads=set(); self.fail_writes=set(); self.fail_watchdog=False
  self._callbacks=(TIME_CB(self._time),READ_CB(self._read),WRITE_CB(self._write),WATCHDOG_CB(self._watchdog),EVENT_CB(self._event)); self.struct=Hal(*self._callbacks)
 def now_us(self): return self._time_us if self.manual else time.monotonic_ns()//1000
 def set_time_us(self,value):
  if not self.manual: raise RuntimeError("manual time is disabled")
  if value<self._time_us: raise ValueError("monotonic time cannot move backwards")
  self._time_us=int(value)
 def advance_time_us(self,value): self.set_time_us(self._time_us+int(value))
 def set_input(self,endpoint,value,type_name): self.inputs[int(endpoint)]=normalize(value,type_name)
 def _time(self,_): return self.now_us()
 def _read(self,_,endpoint,out):
  self.read_count+=1
  if endpoint in self.fail_reads or endpoint not in self.inputs: return 16
  _to_c(self.inputs[endpoint],out.contents); return 0
 def _write(self,_,endpoint,value):
  self.write_count+=1
  if endpoint in self.fail_writes: return 16
  self.outputs[endpoint]=_from_c(value.contents); return 0
 def _watchdog(self,_): self.watchdog_count+=1; return 16 if self.fail_watchdog else 0
 def _event(self,*_): pass

@dataclass(frozen=True)
class RuntimeDiagnostics:
 scan_count:int; last_scan_start_us:int; last_scan_duration_us:int; average_scan_duration_us:int; max_scan_duration_us:int; overrun_count:int; fault_count:int; active_force_count:int; tag_count:int; instruction_count:int; state_slot_count:int; last_instruction_id:int
 def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class RuntimeFault:
 category:str; code:int; scan_number:int; timestamp_us:int; instruction_id:int; tag_id:int; opcode:int; major:bool; message_id:str
@dataclass(frozen=True)
class SnapshotValue: runtime_id:int; logical:object; effective:object; forced:bool
@dataclass(frozen=True)
class RuntimeSnapshot: mode:RuntimeMode; scan_count:int; program_hash:str; values:tuple[SnapshotValue,...]; diagnostics:RuntimeDiagnostics; last_fault:RuntimeFault|None

def _to_c(v,out):
 if isinstance(v,BoolValue): out.type=1; out.value.boolean=v.value
 elif isinstance(v,DintValue): out.type=2; out.value.dint=v.value
 elif isinstance(v,RealValue): out.type=3; out.value.real=v.value
 else: raise TypeError("composite values cannot be written")
def _from_c(v): return BoolValue(bool(v.value.boolean)) if v.type==1 else DintValue(v.value.dint) if v.type==2 else RealValue(float(v.value.real)) if v.type==3 else None

class NativeRuntime:
 def __init__(self,library=None,hal=None):
  self.binding=NativeBinding(library); self.hal=hal or NativeSimulationHAL(); self._object=C.create_string_buffer(self.binding.lib.rsm_runtime_object_size()); self._arena=None; self._image=None; self._closed=False; self._map=None; self._manifest=None; self._lock=threading.RLock()
 def __enter__(self): return self
 def __exit__(self,*_): self.close()
 def _open(self):
  if self._closed: raise RSmicroNativeError("native runtime is closed")
 def validate_image(self,data):
  buf=(C.c_uint8*len(data)).from_buffer_copy(data); info=ImageInfo(); self.binding.check(self.binding.lib.rsm_runtime_validate_image(buf,len(data),C.byref(info)),"validate image"); return info
 def load_image(self,image,manifest=None,debug_map=None):
  data=Path(image).read_bytes() if isinstance(image,(str,Path)) else bytes(image); self.validate_image(data)
  if manifest and manifest.get("image_sha256")!=hashlib.sha256(data).hexdigest(): raise NativeImageError("manifest image hash does not match image")
  self._image=(C.c_uint8*len(data)).from_buffer_copy(data); need=C.c_size_t(); self.binding.check(self.binding.lib.rsm_runtime_required_memory(self._image,len(data),C.byref(need)),"required memory")
  self._arena=C.create_string_buffer(need.value+8); self.binding.check(self.binding.lib.rsm_runtime_init(self._object,self._arena,len(self._arena),C.byref(self.hal.struct),None),"initialize runtime"); self.binding.check(self.binding.lib.rsm_runtime_load_image(self._object,self._image,len(data)),"load image")
  self._manifest=manifest; self._map=debug_map; self.program_hash=hashlib.sha256(data).hexdigest(); return self
 @classmethod
 def from_image(cls,image,**kw): return cls(**kw).load_image(image)
 def close(self):
  if not self._closed: self.binding.lib.rsm_runtime_deinit(self._object); self._closed=True
 def unload(self): self._open(); self.binding.check(self.binding.lib.rsm_runtime_unload_program(self._object),"unload program"); self._image=None
 @property
 def mode(self): self._open(); return RuntimeMode(self.binding.lib.rsm_runtime_get_mode(self._object))
 def set_mode(self,mode): self._open(); self.binding.check(self.binding.lib.rsm_runtime_set_mode(self._object,int(RuntimeMode(mode))),"set mode")
 def scan(self): self._open(); self.binding.check(self.binding.lib.rsm_runtime_scan(self._object),"scan")
 def _id(self,key):
  if isinstance(key,int): return key
  if not self._map: raise NativeTagError("UUID/name access requires a matching debug map")
  hits=[x for x in self._map["tags"] if x["uuid"]==key or x["name"]==key]
  if len(hits)!=1: raise NativeTagError(f"tag name/UUID is {'ambiguous: '+', '.join(x['uuid'] for x in hits) if hits else 'not found'}")
  return hits[0]["runtime_id"]
 def _type(self,key):
  rid=self._id(key)
  if not self._map: raise NativeTagError("typed writes require a debug map")
  return next(x["type"] for x in self._map["tags"] if x["runtime_id"]==rid)
 def read_tag(self,key):
  rid=self._id(key); typ=self._type(rid) if self._map else None
  if typ in ("TIMER","COUNTER"):
   names=("PRE","ACC","EN","TT","DN") if typ=="TIMER" else ("PRE","ACC",None,None,"DN","CU","CD","OV","UN")
   vals=[self.read_member(rid,n) for n in names if n]
   return TimerValue(vals[0].value,vals[1].value,*(x.value for x in vals[2:])) if typ=="TIMER" else CounterValue(vals[0].value,vals[1].value,vals[3].value,vals[4].value,vals[2].value,vals[5].value,vals[6].value)
  v=Value(); self.binding.check(self.binding.lib.rsm_runtime_read_tag(self._object,rid,C.byref(v)),"read tag"); return _from_c(v)
 def read_member(self,key,member):
  ids={"PRE":1,"ACC":2,"EN":3,"TT":4,"DN":5,"CU":6,"CD":7,"OV":8,"UN":9}; v=Value(); self.binding.check(self.binding.lib.rsm_runtime_read_member(self._object,self._id(key),ids.get(str(member).upper(),member),C.byref(v)),"read member"); return _from_c(v)
 def _change(self,fn,key,value):
  rid=self._id(key); v=Value(); _to_c(normalize(value,self._type(rid)),v); self.binding.check(fn(self._object,rid,C.byref(v)),"change tag")
 def write_tag(self,key,value): self._change(self.binding.lib.rsm_runtime_write_tag,key,value)
 def force_tag(self,key,value): self._change(self.binding.lib.rsm_runtime_force_tag,key,value)
 def clear_force(self,key): self.binding.check(self.binding.lib.rsm_runtime_clear_force(self._object,self._id(key)),"clear force")
 def clear_all_forces(self): self.binding.check(self.binding.lib.rsm_runtime_clear_all_forces(self._object),"clear all forces")
 def diagnostics(self):
  d=Diagnostics(); self.binding.check(self.binding.lib.rsm_runtime_get_diagnostics(self._object,C.byref(d)),"diagnostics"); return RuntimeDiagnostics(*(getattr(d,n) for n,_ in d._fields_))
 def last_fault(self):
  p=self.binding.lib.rsm_runtime_last_fault(self._object)
  if not p or p.contents.category==0:return None
  f=p.contents; return RuntimeFault(self.binding.lib.rsm_fault_category_name(f.category).decode(),f.code,f.scan_number,f.timestamp_us,f.instruction_id,f.tag_id,f.opcode,bool(f.major),(f.message_id or b"").decode())
 def snapshot(self):
  values=[]
  @SNAPSHOT_CB
  def cb(_,rid,logical,effective,forced): values.append(SnapshotValue(rid,_from_c(logical.contents),_from_c(effective.contents),bool(forced))); return 0
  writer=SnapshotWriter(None,cb); before=self.diagnostics(); self.binding.check(self.binding.lib.rsm_runtime_snapshot(self._object,C.byref(writer)),"snapshot"); return RuntimeSnapshot(self.mode,before.scan_count,self.program_hash,tuple(values),before,self.last_fault())
