from dataclasses import dataclass
import struct
from .constants import *
from .errors import RsmLinkProtocolError
_HEADER=struct.Struct("<4sBBBBHHIII")
def crc32c(data: bytes)->int:
 crc=0xffffffff
 for byte in data:
  crc^=byte
  for _ in range(8): crc=(crc>>1)^((0x82f63b78)&-(crc&1))
 return (~crc)&0xffffffff
@dataclass(frozen=True)
class Frame:
 message_type:int; payload:bytes=b""; request_id:int=0; sequence:int=0; header_flags:int=0; message_flags:int=0
 def encode(self)->bytes:
  if len(self.payload)>MAX_PAYLOAD_SIZE: raise ValueError("payload exceeds protocol limit")
  body=_HEADER.pack(MAGIC,FRAME_VERSION,PROTOCOL_MAJOR,PROTOCOL_MINOR,self.header_flags,self.message_type,self.message_flags,self.request_id,self.sequence,len(self.payload))+self.payload
  return body+struct.pack("<I",crc32c(body))
 @classmethod
 def decode(cls,data:bytes):
  if len(data)<MIN_FRAME_SIZE: raise RsmLinkProtocolError("truncated frame")
  magic,fv,major,minor,hf,mt,mf,rid,seq,n=_HEADER.unpack_from(data)
  if magic!=MAGIC: raise RsmLinkProtocolError("invalid magic")
  if fv!=FRAME_VERSION or major!=PROTOCOL_MAJOR: raise RsmLinkProtocolError("unsupported version")
  if hf & ~1: raise RsmLinkProtocolError("reserved header flags")
  if n>MAX_PAYLOAD_SIZE or len(data)!=HEADER_SIZE+n+TRAILER_SIZE: raise RsmLinkProtocolError("invalid payload length")
  if crc32c(data[:-4])!=struct.unpack_from("<I",data,len(data)-4)[0]: raise RsmLinkProtocolError("CRC32C mismatch")
  try: MessageType(mt)
  except ValueError:
   if not hf&FrameFlags.OPTIONAL_MESSAGE: raise RsmLinkProtocolError("unsupported required message")
  return cls(mt,data[HEADER_SIZE:-4],rid,seq,hf,mf)
