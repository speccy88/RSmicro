from dataclasses import dataclass,field
from typing import Any
@dataclass(slots=True)
class Scada:
 screens:list[dict[str,Any]]=field(default_factory=list); alarms:list[dict[str,Any]]=field(default_factory=list); historian:dict[str,Any]=field(default_factory=dict); metadata:dict[str,Any]=field(default_factory=dict)
 def to_dict(self): return {"screens":self.screens,"alarms":self.alarms,"historian":self.historian,"metadata":self.metadata}
