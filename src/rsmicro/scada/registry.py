from __future__ import annotations
import asyncio, time
from dataclasses import dataclass, field, asdict
from typing import Any
from .quality import *
from .errors import RegistryError
@dataclass(slots=True)
class LiveTag:
 tag_id:str; controller_id:str; connection_id:str; program_hash:str; runtime_id:int; qualified_name:str; display_name:str; data_type:str
 description:str=""; storage_class:str="memory"; value:Any=None; logical_value:Any=None; effective_value:Any=None; forced:bool=False; readable:bool=True; writable:bool=False; forceable:bool=False; scada_visible:bool=True; engineering_unit:str|None=None; minimum:float|None=None; maximum:float|None=None; source_timestamp:str|None=None; receive_timestamp:str|None=None; scan_number:int=0; source_sequence:int=0; broker_sequence:int=0; quality:Quality=field(default_factory=lambda:Quality.now(QualityLevel.UNCERTAIN,QualityReason.UNCERTAIN_INITIALIZING)); deployment_endpoint:str|None=None; produced:dict|None=None; consumed:dict|None=None; last_change_timestamp:str|None=None; last_good_timestamp:str|None=None
 def to_dict(self):
  d=asdict(self); d["quality"]=self.quality.to_dict(); return d
class TagRegistry:
 def __init__(self): self._tags={}; self._runtime={}; self._lock=asyncio.Lock(); self._sequence=0; self.listeners=[]
 async def replace_manifest(self, controller_id, connection_id, program_hash, manifest):
  async with self._lock:
   for key,t in list(self._tags.items()):
    if t.controller_id==controller_id:
     t.quality=Quality.now(QualityLevel.UNCERTAIN,QualityReason.UNCERTAIN_PROGRAM_CHANGED); self._runtime.pop((controller_id,t.program_hash,t.runtime_id),None)
   for raw in manifest:
    tid=raw.get("tag_uuid") or raw.get("tag_id"); rid=int(raw.get("runtime_id",raw.get("id",0)))
    tag=LiveTag(tid,controller_id,connection_id,program_hash,rid,raw.get("qualified_name",raw.get("name",tid)),raw.get("display_name",raw.get("name",tid)),raw.get("type","BOOL"),description=raw.get("description",""),writable=raw.get("writable",False),forceable=raw.get("forceable",False),scada_visible=raw.get("scada_visible",True),minimum=raw.get("minimum"),maximum=raw.get("maximum"))
    self._tags[(controller_id,tid)]=tag; self._runtime[(controller_id,program_hash,rid)]=tag
 def get(self, identity, controller_id=None):
  if controller_id and (controller_id,identity) in self._tags: return self._tags[(controller_id,identity)]
  found=[t for t in self._tags.values() if t.tag_id==identity or t.qualified_name==identity or (controller_id and t.controller_id==controller_id and t.display_name==identity)]
  if len(found)!=1: raise RegistryError("tag not found" if not found else "ambiguous tag name")
  return found[0]
 async def update(self, controller_id, program_hash, runtime_id, value, *, data_type=None, sequence=0, scan=0, forced=False, source_timestamp=None):
  async with self._lock:
   tag=self._runtime.get((controller_id,program_hash,runtime_id))
   if not tag: raise RegistryError("stale or unknown runtime tag ID")
   if data_type and data_type!=tag.data_type: tag.quality=Quality.now(QualityLevel.BAD,QualityReason.BAD_TYPE_MISMATCH); raise RegistryError("tag type mismatch")
   if sequence and sequence<=tag.source_sequence: return False
   self._sequence+=1; changed=value!=tag.effective_value or forced!=tag.forced; now=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()
   tag.value=tag.logical_value=value; tag.effective_value=value; tag.forced=forced; tag.source_sequence=sequence; tag.scan_number=scan; tag.broker_sequence=self._sequence; tag.source_timestamp=source_timestamp or now; tag.receive_timestamp=now; tag.quality=Quality.now(QualityLevel.GOOD,QualityReason.GOOD_FORCED if forced else QualityReason.GOOD_LIVE,"controller"); tag.last_good_timestamp=now
   if changed: tag.last_change_timestamp=now
  for listener in self.listeners: listener(tag)
  return True
 async def mark_controller_stale(self, controller_id):
  changed=[]
  async with self._lock:
   for t in self._tags.values():
    if t.controller_id==controller_id: t.quality=Quality.now(QualityLevel.STALE,QualityReason.STALE_CONTROLLER_TIMEOUT); changed.append(t)
  for t in changed:
   for listener in self.listeners: listener(t)
 def all(self): return list(self._tags.values())
