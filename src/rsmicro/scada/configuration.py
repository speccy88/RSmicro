from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import ipaddress, json, uuid
from .errors import ConfigurationError

@dataclass(slots=True)
class ReconnectConfig:
 enabled: bool=True; initial_delay_ms:int=250; maximum_delay_ms:int=5000; maximum_attempts:int=0
@dataclass(slots=True)
class ControllerConfig:
 controller_id:str=""; host:str="127.0.0.1"; port:int=7580; connect_timeout_ms:int=2000; request_timeout_ms:int=2000; heartbeat_period_ms:int=1000; stale_timeout_ms:int=3000; reconnect:ReconnectConfig=field(default_factory=ReconnectConfig); required:bool=True
@dataclass(slots=True)
class BrokerConfig:
 broker_id:str; controllers:list[ControllerConfig]; format:str="rsmicro-tagd-config"; format_version:int=1; project:str|None=None; api:dict[str,Any]=field(default_factory=lambda:{"listen":"127.0.0.1","port":7590}); historian:dict[str,Any]=field(default_factory=dict); alarms:dict[str,Any]=field(default_factory=dict); routing:dict[str,Any]=field(default_factory=dict); limits:dict[str,Any]=field(default_factory=dict)
 def validate(self, allow_external=False):
  if self.format!="rsmicro-tagd-config" or self.format_version!=1: raise ConfigurationError("unsupported broker configuration format")
  try: uuid.UUID(self.broker_id)
  except ValueError as e: raise ConfigurationError("broker_id must be a UUID") from e
  ids=set(); endpoints=set()
  for c in self.controllers:
   if c.controller_id in ids: raise ConfigurationError(f"duplicate controller_id: {c.controller_id}")
   if (c.host,c.port) in endpoints: raise ConfigurationError(f"duplicate controller endpoint: {c.host}:{c.port}")
   ids.add(c.controller_id); endpoints.add((c.host,c.port))
   if not 1<=c.port<=65535 or c.stale_timeout_ms<=0 or c.heartbeat_period_ms<=0: raise ConfigurationError("controller port and timeouts must be positive")
   if c.reconnect.initial_delay_ms<1 or c.reconnect.maximum_delay_ms<c.reconnect.initial_delay_ms or c.reconnect.maximum_delay_ms>300000 or c.reconnect.maximum_attempts<0: raise ConfigurationError("invalid bounded reconnect policy")
  host=self.api.get("listen","127.0.0.1")
  try: loop=ipaddress.ip_address(host).is_loopback
  except ValueError: loop=host=="localhost"
  if not loop and not allow_external: raise ConfigurationError("non-loopback API binding requires explicit allow_external")
  return self
 def to_json(self): return json.dumps(asdict(self),sort_keys=True,separators=(",",":"))+"\n"
def load_config(path, *, allow_external=False):
 raw=json.loads(Path(path).read_text(encoding="utf-8")); allowed={"format","format_version","broker_id","project","controllers","api","historian","alarms","routing","limits"}
 unknown=set(raw)-allowed
 if unknown: raise ConfigurationError("unknown configuration fields: "+", ".join(sorted(unknown)))
 cs=[]
 for item in raw.get("controllers",[]):
  item=dict(item); item["reconnect"]=ReconnectConfig(**item.get("reconnect",{})); cs.append(ControllerConfig(**item))
 return BrokerConfig(**{**raw,"controllers":cs}).validate(allow_external)
