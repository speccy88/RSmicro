from __future__ import annotations
import time
from dataclasses import dataclass
from datetime import datetime,timezone
from enum import StrEnum
from .alarm_models import *
class AlarmState(StrEnum): NORMAL="NORMAL"; PENDING_ACTIVE="PENDING_ACTIVE"; ACTIVE_UNACKNOWLEDGED="ACTIVE_UNACKNOWLEDGED"; ACTIVE_ACKNOWLEDGED="ACTIVE_ACKNOWLEDGED"; PENDING_RETURN="PENDING_RETURN"; RETURNED_UNACKNOWLEDGED="RETURNED_UNACKNOWLEDGED"; SHELVED="SHELVED"; DISABLED="DISABLED"
@dataclass(slots=True)
class AlarmRuntime:
 definition:AlarmDefinition; state:AlarmState=AlarmState.NORMAL; state_version:int=0; deadline:float|None=None; active_acknowledged:bool=False; last_transition:str|None=None
class AlarmEngine:
 def __init__(self,definitions=(),clock=time.monotonic): self.alarms={d.alarm_id:AlarmRuntime(d,AlarmState.NORMAL if d.enabled else AlarmState.DISABLED) for d in definitions}; self.clock=clock; self.listeners=[]
 def _condition(self,a,tag):
  c=a.definition.condition; v=tag.effective_value; level=tag.quality.level.name
  if c==AlarmCondition.BOOL_TRUE:return v is True
  if c==AlarmCondition.BOOL_FALSE:return v is False
  if c==AlarmCondition.BAD_QUALITY:return level=="BAD"
  if c==AlarmCondition.STALE_QUALITY:return level=="STALE"
  active=a.state not in (AlarmState.NORMAL,AlarmState.PENDING_ACTIVE,AlarmState.DISABLED)
  h=a.definition.hysteresis; t=a.definition.threshold
  return v>=(t-h if active and c in (AlarmCondition.HIGH,AlarmCondition.HIGH_HIGH) else t) if c in (AlarmCondition.HIGH,AlarmCondition.HIGH_HIGH) else v<=(t+h if active else t)
 def evaluate(self,alarm_id,tag):
  a=self.alarms[alarm_id]; now=self.clock(); cond=self._condition(a,tag)
  if a.state==AlarmState.NORMAL and cond: self._move(a,AlarmState.PENDING_ACTIVE,a.definition.delay_on_ms,now)
  if a.state==AlarmState.PENDING_ACTIVE:
   if not cond:self._move(a,AlarmState.NORMAL)
   elif a.deadline is None or now>=a.deadline:self._move(a,AlarmState.ACTIVE_UNACKNOWLEDGED)
  elif a.state in (AlarmState.ACTIVE_UNACKNOWLEDGED,AlarmState.ACTIVE_ACKNOWLEDGED) and not cond:
   acknowledged=a.active_acknowledged
   self._move(a,AlarmState.PENDING_RETURN,a.definition.delay_off_ms,now)
   if not a.definition.delay_off_ms:self._move(a,AlarmState.NORMAL if acknowledged or not a.definition.acknowledgement_required else AlarmState.RETURNED_UNACKNOWLEDGED)
  elif a.state==AlarmState.PENDING_RETURN:
   if cond:self._move(a,AlarmState.ACTIVE_ACKNOWLEDGED if a.active_acknowledged else AlarmState.ACTIVE_UNACKNOWLEDGED)
   elif a.deadline is None or now>=a.deadline:self._move(a,AlarmState.NORMAL if a.active_acknowledged or not a.definition.acknowledgement_required else AlarmState.RETURNED_UNACKNOWLEDGED)
  return a
 def acknowledge(self,alarm_id,requester,state_version=None,comment=None):
  a=self.alarms[alarm_id]
  if state_version is not None and state_version!=a.state_version: raise ValueError("stale alarm state version")
  if a.state==AlarmState.ACTIVE_UNACKNOWLEDGED: a.active_acknowledged=True; self._move(a,AlarmState.ACTIVE_ACKNOWLEDGED)
  elif a.state==AlarmState.RETURNED_UNACKNOWLEDGED:self._move(a,AlarmState.NORMAL)
  elif a.state not in (AlarmState.ACTIVE_ACKNOWLEDGED,AlarmState.NORMAL): raise ValueError("alarm cannot be acknowledged in current state")
  return a
 def _move(self,a,state,delay=0,now=None):
  if a.state==state:return
  a.state=state;a.state_version+=1;a.last_transition=datetime.now(timezone.utc).isoformat();a.deadline=(now if now is not None else self.clock())+delay/1000 if delay else None
  for f in self.listeners:f(a)
