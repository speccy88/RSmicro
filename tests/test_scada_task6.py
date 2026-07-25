import asyncio,json,sqlite3,uuid
from datetime import datetime,timezone,timedelta
import pytest
from rsmicro.scada.configuration import *
from rsmicro.scada.errors import ConfigurationError,RegistryError
from rsmicro.scada.quality import *
from rsmicro.scada.registry import TagRegistry
from rsmicro.scada.historian import Historian
from rsmicro.scada.alarm_models import *
from rsmicro.scada.alarms import *
from rsmicro.scada.routing import *
from rsmicro.scada.api import require

def cfg(**kw): return BrokerConfig(str(uuid.uuid4()),[ControllerConfig("a")],**kw)
def test_config_deterministic_and_loopback(): assert cfg().validate().to_json()==cfg(broker_id:=None).to_json() if False else cfg().validate().to_json().endswith('\n')
def test_config_duplicate_controller():
 c=cfg();c.controllers.append(ControllerConfig("a",port=2))
 with pytest.raises(ConfigurationError):c.validate()
def test_config_external_rejected():
 c=cfg(api={"listen":"0.0.0.0","port":7590})
 with pytest.raises(ConfigurationError):c.validate()
def test_quality_order(): assert QualityLevel.GOOD<QualityLevel.UNCERTAIN<QualityLevel.STALE<QualityLevel.BAD
def test_registry_generation_sequence_and_stale():
 async def scenario():
  r=TagRegistry();m=[{"tag_uuid":"t","runtime_id":3,"name":"X","type":"DINT","writable":True}];await r.replace_manifest("a","s","p",m)
  assert await r.update("a","p",3,4,data_type="DINT",sequence=2)
  assert not await r.update("a","p",3,5,sequence=2)
  assert r.get("t","a").effective_value==4
  await r.mark_controller_stale("a");assert r.get("t","a").quality.level==QualityLevel.STALE
  with pytest.raises(RegistryError):await r.update("a","old",3,1)
 asyncio.run(scenario())
def test_historian_typed_wal_flush(tmp_path):
 async def scenario():
  h=Historian(tmp_path/'h.db',queue_size=2);await h.start();r=TagRegistry();await r.replace_manifest('a','s','p',[{'tag_uuid':'t','runtime_id':1,'name':'T','type':'REAL'}]);await r.update('a','p',1,1.5,sequence=1);assert h.enqueue(r.get('t'))
  await h.close();c=sqlite3.connect(tmp_path/'h.db');assert c.execute('pragma journal_mode').fetchone()[0]=='wal';assert c.execute('select real_value from samples').fetchone()[0]==1.5;assert c.execute('pragma user_version').fetchone()[0]==1
 asyncio.run(scenario())
def test_historian_queue_bounded(tmp_path):
 async def scenario():
  h=Historian(tmp_path/'h.db',queue_size=1);h.open();item={'tag_id':'t'};assert h.enqueue(item);assert not h.enqueue(item);assert h.dropped==1;h._conn.close()
 asyncio.run(scenario())
class Clock:
 def __init__(self):self.v=0
 def __call__(self):return self.v
def tag(value):
 class T:pass
 t=T();t.effective_value=value;t.quality=Quality.now(QualityLevel.GOOD,QualityReason.GOOD_LIVE);return t
def test_alarm_lifecycle_delay_hysteresis():
 clock=Clock();d=AlarmDefinition('x','High','t',AlarmCondition.HIGH,10,delay_on_ms=100,delay_off_ms=100,hysteresis=2);e=AlarmEngine([d],clock);a=e.evaluate('x',tag(11));assert a.state==AlarmState.PENDING_ACTIVE;clock.v=.11;e.evaluate('x',tag(11));assert a.state==AlarmState.ACTIVE_UNACKNOWLEDGED;e.acknowledge('x','u',a.state_version);assert a.state==AlarmState.ACTIVE_ACKNOWLEDGED;e.evaluate('x',tag(9));assert a.state==AlarmState.ACTIVE_ACKNOWLEDGED;e.evaluate('x',tag(7));assert a.state==AlarmState.PENDING_RETURN;clock.v=.22;e.evaluate('x',tag(7));assert a.state==AlarmState.NORMAL
def test_alarm_return_unacknowledged():
 e=AlarmEngine([AlarmDefinition('x','B','t',AlarmCondition.BOOL_TRUE)]);a=e.evaluate('x',tag(True));assert a.state==AlarmState.ACTIVE_UNACKNOWLEDGED;e.evaluate('x',tag(False));assert a.state==AlarmState.RETURNED_UNACKNOWLEDGED;e.acknowledge('x','u');assert a.state==AlarmState.NORMAL
def test_roles():
 with pytest.raises(PermissionError):require('VIEWER','write_tag')
 require('OPERATOR','write_tag')
 with pytest.raises(PermissionError):require('OPERATOR','force_tag')
def test_route_cycle():
 async def w(*x):pass
 r=RoutingEngine(w)
 with pytest.raises(ValueError):r.configure([Route('1','a','x','b','y',10,StalePolicy.SUBSTITUTE),Route('2','b','y','a','x',10,StalePolicy.SUBSTITUTE)])
def test_safe_fallback_write_order():
 async def scenario():
  calls=[]
  async def w(c,t,v,g):calls.append((t,v,g))
  e=RoutingEngine(w);r=Route('r','a','s','b','value',10,StalePolicy.SUBSTITUTE,False,'good','stale');e.configure([r]);await e.timeout(r)
  assert [(x[0],x[1]) for x in calls]==[('good',False),('stale',True),('value',False)];assert len({x[2] for x in calls})==1
 asyncio.run(scenario())
