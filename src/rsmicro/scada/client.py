from __future__ import annotations
import asyncio,json,uuid
class ScadaClient:
 def __init__(self,host="127.0.0.1",port=7590,timeout=5,role="VIEWER"):self.uri=f"ws://{host}:{port}";self.timeout=timeout;self.role=role.upper();self.ws=None
 async def connect(self):
  from websockets.asyncio.client import connect
  self.ws=await connect(self.uri);await self.request("hello");return self
 async def request(self,kind,**payload):
  rid=str(uuid.uuid4());await self.ws.send(json.dumps({"type":kind,"request_id":rid,"role":self.role,**payload}));result=json.loads(await asyncio.wait_for(self.ws.recv(),self.timeout))
  if result["type"]=="error":raise RuntimeError(result["message"])
  return result
 async def service_info(self):return await self.request("get_service_info")
 async def controllers(self):return await self.request("get_controllers")
 async def tags(self):return await self.request("get_tag_manifest")
 async def read(self,tag):return await self.request("read_tag",tag=tag)
 async def write(self,tag,value,requester="local"):return await self.request("write_tag",tag=tag,value=value,requester=requester)
 async def force(self,tag,value):return await self.request("force_tag",tag=tag,value=value)
 async def unforce(self,tag):return await self.request("clear_force",tag=tag)
 async def history(self,tag_uuid,start,end,maximum_points=1000):return await self.request("query_history",tag_uuid=tag_uuid,**{"from":start,"to":end},maximum_points=maximum_points)
 async def alarms(self):return await self.request("get_alarm_state")
 async def acknowledge(self,alarm_id,requester,comment="",state_version=None):return await self.request("acknowledge_alarm",alarm_id=alarm_id,requester=requester,comment=comment,state_version=state_version)
 async def routes(self):return await self.request("get_routes")
 async def diagnostics(self):return await self.request("get_diagnostics")
 async def close(self):
  if self.ws:await self.ws.close()
 async def __aenter__(self):return await self.connect()
 async def __aexit__(self,*_):await self.close()
