from __future__ import annotations
import asyncio, random, time
from rsmicro.protocol.client import RsmLinkClient
from .controller import ControllerState,ALLOWED_TRANSITIONS
class ControllerSupervisor:
 def __init__(self,config,registry,client_factory=RsmLinkClient): self.config=config;self.registry=registry;self.client_factory=client_factory;self.state=ControllerState.DISCONNECTED;self.client=None;self.reconnect_count=0;self.program_hash=None;self.activation_generation=None;self.connection_id=None;self.last_seen=0.;self._stop=False;self._task=None
 def transition(self,state):
  if state not in ALLOWED_TRANSITIONS.get(self.state,set()): raise RuntimeError(f"invalid controller transition {self.state} -> {state}")
  self.state=state
 async def start(self): self._task=asyncio.create_task(self.run()); return self
 async def run(self):
  attempt=0
  while not self._stop:
   try:
    self.transition(ControllerState.CONNECTING); self.client=self.client_factory(self.config.host,self.config.port,self.config.request_timeout_ms/1000); await self.client.connect(); self.transition(ControllerState.NEGOTIATING); caps=await self.client.get_capabilities(); info=await self.client.get_program_info()
    remote=info.get("controller_uuid") or caps.get("controller_uuid")
    if remote and remote!=self.config.controller_id: raise RuntimeError("controller identity mismatch")
    self.transition(ControllerState.SYNCHRONIZING); self.connection_id=info.get("session_id",str(id(self.client))); self.program_hash=info.get("program_hash",""); self.activation_generation=info.get("activation_generation",0)
    manifest=info.get("tag_manifest",caps.get("tag_manifest",[])); await self.registry.replace_manifest(self.config.controller_id,self.connection_id,self.program_hash,manifest); self.last_seen=time.monotonic(); self.transition(ControllerState.ONLINE); attempt=0
    while not self._stop:
     await asyncio.sleep(self.config.heartbeat_period_ms/1000); await self.client.get_diagnostics(); self.last_seen=time.monotonic()
   except asyncio.CancelledError: break
   except Exception:
    if self.state in (ControllerState.ONLINE,ControllerState.DEGRADED): self.transition(ControllerState.STALE); await self.registry.mark_controller_stale(self.config.controller_id)
    if self.state!=ControllerState.RECONNECTING: self.state=ControllerState.RECONNECTING
    attempt+=1;self.reconnect_count+=1
    if not self.config.reconnect.enabled or (self.config.reconnect.maximum_attempts and attempt>self.config.reconnect.maximum_attempts): self.state=ControllerState.FAULTED; break
    delay=min(self.config.reconnect.maximum_delay_ms,self.config.reconnect.initial_delay_ms*2**min(attempt-1,16))/1000; await asyncio.sleep(delay)
  if self.client: await self.client.close()
  self.state=ControllerState.CLOSED
 async def stop(self):
  self._stop=True
  if self.state not in (ControllerState.CLOSED,ControllerState.STOPPING): self.state=ControllerState.STOPPING
  if self._task: self._task.cancel(); await asyncio.gather(self._task,return_exceptions=True)
  if self.client: await self.client.close()
  self.state=ControllerState.CLOSED
