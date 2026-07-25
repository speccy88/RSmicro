from __future__ import annotations
from dataclasses import dataclass,field
from enum import StrEnum
from typing import Any
class TagType(StrEnum): BOOL="BOOL"; DINT="DINT"; REAL="REAL"; TIMER="TIMER"; COUNTER="COUNTER"
TIMER_MEMBERS={"PRE","ACC","EN","TT","DN"}; COUNTER_MEMBERS={"PRE","ACC","CU","CD","DN","OV","UN"}
@dataclass(slots=True)
class Tag:
 tag_id:str; name:str; data_type:TagType; description:str=""; initial_value:bool|int|float|None=None; preset:int|None=None; retentive:bool=False; writable:bool=True; access:dict[str,Any]=field(default_factory=dict); engineering_unit:str|None=None; minimum:int|float|None=None; maximum:int|float|None=None; scada_visible:bool=True; metadata:dict[str,Any]=field(default_factory=dict)
 def to_dict(self):
  return {"tag_id":self.tag_id,"name":self.name,"description":self.description,"data_type":str(self.data_type),"initial_value":self.initial_value,"preset":self.preset,"retentive":self.retentive,"writable":self.writable,"access":self.access,"engineering_unit":self.engineering_unit,"minimum":self.minimum,"maximum":self.maximum,"scada_visible":self.scada_visible,"metadata":self.metadata}
