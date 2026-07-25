from .constants import HEADER_SIZE,MIN_FRAME_SIZE,MAX_FRAME_SIZE,MAX_PAYLOAD_SIZE
from .errors import RsmLinkProtocolError
from .frame import Frame
import struct
class StreamDecoder:
 def __init__(self,max_frame_size=MAX_FRAME_SIZE): self.max_frame_size=min(max_frame_size,MAX_FRAME_SIZE); self.buffer=bytearray(); self.failed=False
 def feed(self,data:bytes):
  if self.failed: raise RsmLinkProtocolError("decoder failed; reset required")
  if len(self.buffer)+len(data)>self.max_frame_size: self.failed=True; raise RsmLinkProtocolError("stream buffer limit")
  self.buffer.extend(data); out=[]
  try:
   while len(self.buffer)>=HEADER_SIZE:
    n=struct.unpack_from("<I",self.buffer,20)[0]
    if n>MAX_PAYLOAD_SIZE or HEADER_SIZE+n+4>self.max_frame_size: raise RsmLinkProtocolError("excessive payload")
    total=HEADER_SIZE+n+4
    if len(self.buffer)<total: break
    out.append(Frame.decode(bytes(self.buffer[:total]))); del self.buffer[:total]
  except RsmLinkProtocolError: self.failed=True; self.buffer.clear(); raise
  return out
 def close(self):
  if self.buffer: self.failed=True; self.buffer.clear(); raise RsmLinkProtocolError("connection closed with partial frame")
 def reset(self): self.buffer.clear(); self.failed=False
