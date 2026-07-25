from __future__ import annotations
import asyncio
from enum import Enum
from .constants import MessageType
from .errors import *
from .frame import Frame
from .messages import encode_message,decode_message
from .stream import StreamDecoder
class ConnectionState(Enum): DISCONNECTED="disconnected"; CONNECTING="connecting"; NEGOTIATING="negotiating"; CONNECTED="connected"; DEGRADED="degraded"; STALE="stale"; CLOSED="closed"
class RsmLinkClient:
 def __init__(self,host="127.0.0.1",port=7580,timeout=5.0): self.host=host; self.port=port; self.timeout=timeout; self.state=ConnectionState.DISCONNECTED; self._next=1; self._pending={}; self._decoder=StreamDecoder(); self._reader=None; self._writer=None; self._task=None; self.capabilities=None
 async def connect(self):
  self.state=ConnectionState.CONNECTING
  try: self._reader,self._writer=await asyncio.wait_for(asyncio.open_connection(self.host,self.port),self.timeout)
  except (OSError,asyncio.TimeoutError) as e: self.state=ConnectionState.DISCONNECTED; raise RsmLinkConnectionError(str(e)) from e
  self.state=ConnectionState.NEGOTIATING; self._task=asyncio.create_task(self._receive()); await self.request(MessageType.HELLO,{"client_name":"rsmicro","protocol_major":1,"protocol_minor":0}); self.state=ConnectionState.CONNECTED; return self
 async def _receive(self):
  try:
   while data:=await self._reader.read(65536):
    for frame in self._decoder.feed(data):
     future=self._pending.pop(frame.request_id,None)
     if future and not future.done(): future.set_result((frame.message_type,decode_message(frame.payload)))
  except Exception as e:
   for f in self._pending.values():
    if not f.done(): f.set_exception(RsmLinkConnectionError(str(e)))
  finally: self._pending.clear()
 async def request(self,message_type,payload=None):
  rid=self._next; self._next=(rid+1)&0xffffffff or 1; future=asyncio.get_running_loop().create_future(); self._pending[rid]=future
  self._writer.write(Frame(int(message_type),encode_message(payload or {}),rid).encode()); await self._writer.drain()
  try: mt,result=await asyncio.wait_for(future,self.timeout)
  except asyncio.TimeoutError as e: self._pending.pop(rid,None); raise RsmLinkTimeoutError(f"request {rid} timed out") from e
  if mt==MessageType.ERROR: raise RsmLinkRemoteError(result.get("identifier","remote error"),request_id=rid,code=result.get("error_code",255),recoverable=result.get("recoverable",False),details=result)
  return result
 async def get_capabilities(self): self.capabilities=await self.request(MessageType.CAPABILITIES_REQUEST); return self.capabilities
 async def get_program_info(self): return await self.request(MessageType.GET_PROGRAM_INFO)
 async def get_mode(self): return await self.request(MessageType.GET_MODE)
 async def set_mode(self,mode): return await self.request(MessageType.SET_MODE,{"mode":str(mode).upper()})
 async def get_diagnostics(self): return await self.request(MessageType.GET_DIAGNOSTICS)
 async def close(self):
  if self._writer: self._writer.close(); await self._writer.wait_closed()
  if self._task: self._task.cancel()
  self.state=ConnectionState.CLOSED
 async def __aenter__(self): return await self.connect()
 async def __aexit__(self,*_): await self.close()
