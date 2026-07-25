from __future__ import annotations
import asyncio,json
from .messages import decode_message,response,MAX_MESSAGE_SIZE
from .api import require
class LocalApiServer:
 def __init__(self,service,host="127.0.0.1",port=7590,max_clients=16): self.service=service;self.host=host;self.port=port;self.max_clients=max_clients;self.server=None;self.clients=set()
 async def start(self):
  try: from websockets.asyncio.server import serve
  except ImportError: from websockets import serve
  self.server=await serve(self._handle,self.host,self.port,max_size=MAX_MESSAGE_SIZE,max_queue=32);return self
 async def _handle(self,ws):
  if len(self.clients)>=self.max_clients: await ws.close(1013,"client limit");return
  self.clients.add(ws)
  try:
   async for raw in ws:
    try:
     m=decode_message(raw); typ=m["type"]; rid=m.get("request_id"); role=m.get("role","VIEWER").upper()
     if typ=="hello": out=response("hello_response",rid,protocol="rsmicro-scada-json",protocol_version=1,warning="roles are local policy hints, not authentication")
     elif typ=="get_service_info": out=response("service_info",rid,**self.service.info())
     elif typ=="get_controllers": out=response("controllers",rid,controllers=self.service.controllers_info())
     elif typ=="get_tag_manifest": out=response("tag_manifest",rid,tags=[t.to_dict() for t in self.service.registry.all()])
     elif typ=="read_tag": out=response("tag_update",rid,tag=self.service.registry.get(m["tag"],m.get("controller_id")).to_dict())
     elif typ=="get_diagnostics": out=response("diagnostics",rid,diagnostics=self.service.diagnostics())
     elif typ=="get_routes": out=response("routes",rid,routes=self.service.route_diagnostics())
     elif typ=="get_alarm_state": out=response("alarm_state",rid,alarms=self.service.alarm_states())
     elif typ=="write_tag": require(role,typ); out=response("ack",rid,command=await self.service.write(m["tag"],m["value"],m.get("requester","local")))
     elif typ in ("force_tag","clear_force","clear_all_forces"): require(role,typ); out=response("ack",rid,command=await self.service.force(typ,m))
     elif typ=="query_history": out=response("history_result",rid,samples=self.service.historian.query(m["tag_uuid"],m["from"],m["to"],m.get("maximum_points",1000),m.get("quality")))
     elif typ=="acknowledge_alarm": require(role,"write_tag"); out=response("ack",rid,alarm=self.service.acknowledge(m))
     elif typ=="heartbeat": out=response("heartbeat_response",rid)
     else: raise ValueError("unsupported message type")
    except Exception as e: out=response("error",m.get("request_id") if 'm' in locals() else None,code="REQUEST_REJECTED",message=str(e))
    await ws.send(json.dumps(out,separators=(",",":"),default=str))
  finally:self.clients.discard(ws)
 async def close(self):
  if self.server:self.server.close();await self.server.wait_closed()
