import json
MAX_MESSAGE_SIZE=1_048_576
def decode_message(raw):
 if len(raw)>MAX_MESSAGE_SIZE: raise ValueError("message exceeds service limit")
 value=json.loads(raw)
 if not isinstance(value,dict) or not isinstance(value.get("type"),str): raise ValueError("message object requires type")
 return value
def response(kind,request_id=None,**payload): return {"type":kind,"request_id":request_id,**payload}
