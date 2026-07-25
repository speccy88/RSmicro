from __future__ import annotations
import time, uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any
class StalePolicy(StrEnum): HOLD_LAST_UNCERTAIN="HOLD_LAST_UNCERTAIN"; HOLD_LAST_STALE="HOLD_LAST_STALE"; SUBSTITUTE="SUBSTITUTE"; BAD_NO_WRITE="BAD_NO_WRITE"
@dataclass(slots=True)
class Route:
 route_id:str; source_controller_id:str; source_tag_id:str; destination_controller_id:str; destination_tag_id:str; timeout_ms:int; stale_policy:StalePolicy; substitute_value:Any=None; quality_good_tag_id:str|None=None; stale_tag_id:str|None=None; bad_tag_id:str|None=None; enabled:bool=True; deadband:float=0; minimum_interval_ms:int=0
class RoutingEngine:
 def __init__(self,writer): self.writer=writer;self.routes={};self.diagnostics={}
 def configure(self,routes):
  graph={}
  for r in routes:
   if r.destination_tag_id==r.source_tag_id and r.destination_controller_id==r.source_controller_id: raise ValueError("route cycle")
   graph.setdefault((r.source_controller_id,r.source_tag_id),[]).append((r.destination_controller_id,r.destination_tag_id)); self.routes[r.route_id]=r; self.diagnostics[r.route_id]={"route_sequence":0,"stale_count":0,"write_failure_count":0,"last_source_time":None,"quality":"UNCERTAIN"}
  def visit(n,path):
   if n in path: raise ValueError("cyclic produced/consumed route graph")
   for x in graph.get(n,[]):visit(x,path|{n})
  for n in graph:visit(n,set())
 async def source_update(self,r,tag):
  d=self.diagnostics[r.route_id]; now=time.monotonic(); old=d.get("last_value")
  if old is not None and isinstance(old,(int,float)) and abs(tag.effective_value-old)<r.deadband:return
  if d["last_source_time"] and (now-d["last_source_time"])*1000<r.minimum_interval_ms:return
  d.update(last_source_time=now,last_value=tag.effective_value,route_sequence=d["route_sequence"]+1,quality=tag.quality.level.name)
  # Energizing order is value, stale false, quality-good true. Loss uses the inverse safe order below.
  await self.writer(r.destination_controller_id,r.destination_tag_id,tag.effective_value,str(uuid.uuid4()))
  if r.stale_tag_id: await self.writer(r.destination_controller_id,r.stale_tag_id,False,str(uuid.uuid4()))
  if r.quality_good_tag_id: await self.writer(r.destination_controller_id,r.quality_good_tag_id,tag.quality.level.name=="GOOD",str(uuid.uuid4()))
 async def timeout(self,r):
  d=self.diagnostics[r.route_id];d["stale_count"]+=1;d["quality"]="STALE"
  if r.stale_policy==StalePolicy.SUBSTITUTE:
   group=str(uuid.uuid4())
   # Fail-safe order ensures ladder interlocks drop before the consumed value changes.
   if r.quality_good_tag_id:await self.writer(r.destination_controller_id,r.quality_good_tag_id,False,group)
   if r.stale_tag_id:await self.writer(r.destination_controller_id,r.stale_tag_id,True,group)
   if r.bad_tag_id:await self.writer(r.destination_controller_id,r.bad_tag_id,False,group)
   await self.writer(r.destination_controller_id,r.destination_tag_id,r.substitute_value,group)
