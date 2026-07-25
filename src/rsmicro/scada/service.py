from __future__ import annotations
import asyncio,time,uuid
from datetime import datetime,timezone
from rsmicro.protocol import MessageType
from .registry import TagRegistry
from .supervisor import ControllerSupervisor
from .historian import Historian
from .alarms import AlarmEngine
from .websocket_server import LocalApiServer
class ServiceHealth:
 STARTING="STARTING";HEALTHY="HEALTHY";DEGRADED="DEGRADED";UNHEALTHY="UNHEALTHY";STOPPING="STOPPING";STOPPED="STOPPED"
class TagBrokerService:
 def __init__(self,config,database=None):
  self.config=config;self.registry=TagRegistry();self.started=time.monotonic();self.health=ServiceHealth.STARTING;self.historian=Historian(database or config.historian.get("database","history.sqlite3"));self.alarms=AlarmEngine();self.supervisors={c.controller_id:ControllerSupervisor(c,self.registry) for c in config.controllers};self.api=LocalApiServer(self,config.api.get("listen","127.0.0.1"),config.api.get("port",7590),config.limits.get("maximum_clients",16));self.accept_commands=True;self.failed_commands=0
  self.registry.listeners.append(self.historian.enqueue)
 async def start(self):
  await self.historian.start();await self.api.start()
  for s in self.supervisors.values():await s.start()
  self.health=ServiceHealth.HEALTHY;return self
 def info(self):return {"service":"rsmicro-tagd","version":"0.1.0","broker_id":self.config.broker_id,"health":self.health,"uptime_seconds":time.monotonic()-self.started,"api_protocol":"rsmicro-scada-json/1"}
 def controllers_info(self):return [{"controller_id":k,"state":s.state.value,"program_hash":s.program_hash,"activation_generation":s.activation_generation,"reconnect_count":s.reconnect_count} for k,s in self.supervisors.items()]
 def diagnostics(self):
  tags=self.registry.all();return {**self.info(),"controller_states":{k:s.state.value for k,s in self.supervisors.items()},"tag_count":len(tags),"stale_tag_count":sum(t.quality.level.name=="STALE" for t in tags),"bad_tag_count":sum(t.quality.level.name=="BAD" for t in tags),"active_force_count":sum(t.forced for t in tags),"historian_queue_depth":self.historian.queue.qsize(),"historian_queue_high_water":self.historian.high_water,"historian_dropped_samples":self.historian.dropped,"database_write_count":self.historian.write_count,"database_error_count":self.historian.errors,"failed_commands":self.failed_commands,"api_clients":len(self.api.clients)}
 def route_diagnostics(self):return []
 def alarm_states(self):return [{"alarm_id":k,"state":a.state.value,"state_version":a.state_version} for k,a in self.alarms.alarms.items()]
 async def write(self,identity,value,requester):
  if not self.accept_commands:raise RuntimeError("service is stopping")
  tag=self.registry.get(identity);sup=self.supervisors[tag.controller_id]
  if sup.state.value!="ONLINE":raise RuntimeError("controller is not online")
  if not tag.writable:raise RuntimeError("tag is read-only")
  if tag.minimum is not None and value<tag.minimum or tag.maximum is not None and value>tag.maximum:raise ValueError("value outside engineering range")
  if sup.client is None: raise RuntimeError("controller client is unavailable")
  command=str(uuid.uuid4());result=await sup.client.request(MessageType.WRITE_TAG,{"runtime_id":tag.runtime_id,"program_hash":tag.program_hash,"value":value,"command_uuid":command});return {"command_uuid":command,"controller_result":result}
 async def force(self,operation,message):
  tag=self.registry.get(message["tag"]);sup=self.supervisors[tag.controller_id]
  if not tag.forceable:raise RuntimeError("tag is not forceable")
  if sup.client is None: raise RuntimeError("controller client is unavailable")
  mt=MessageType.FORCE_TAG if operation=="force_tag" else MessageType.CLEAR_FORCE
  return await sup.client.request(mt,{"runtime_id":tag.runtime_id,"program_hash":tag.program_hash,"value":message.get("value")})
 def acknowledge(self,m):
  a=self.alarms.acknowledge(m["alarm_id"],m.get("requester","local"),m.get("state_version"),m.get("comment"));return {"alarm_id":a.definition.alarm_id,"state":a.state.value,"state_version":a.state_version}
 async def close(self):
  self.health=ServiceHealth.STOPPING;self.accept_commands=False;await self.api.close();await asyncio.gather(*(s.stop() for s in self.supervisors.values()));await self.historian.close();self.health=ServiceHealth.STOPPED
