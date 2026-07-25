import struct
import pytest
from rsmicro.protocol import Frame,MessageType,StreamDecoder,crc32c,encode_message,decode_message,RsmLinkProtocolError
def test_frame_roundtrip_and_crc():
 payload=encode_message({"name":"client","enabled":True,"count":-2}); raw=Frame(MessageType.HELLO,payload,42,7).encode(); decoded=Frame.decode(raw)
 assert decoded.request_id==42 and decode_message(decoded.payload)["enabled"] is True
 assert struct.unpack_from("<I",raw,len(raw)-4)[0]==crc32c(raw[:-4])
def test_fragmentation_multiple_and_failure_policy():
 a=Frame(MessageType.ACK,b"").encode(); d=StreamDecoder(); result=[]
 for byte in a+a: result.extend(d.feed(bytes([byte])))
 assert len(result)==2
 bad=bytearray(a);bad[-1]^=1
 with pytest.raises(RsmLinkProtocolError): d.feed(bad)
 with pytest.raises(RsmLinkProtocolError): d.feed(a)
 d.reset();assert len(d.feed(a))==1
def test_canonical_bool_and_bounds():
 bad=bytearray(encode_message({"x":True}));bad[-1]=2
 with pytest.raises(ValueError): decode_message(bytes(bad))
