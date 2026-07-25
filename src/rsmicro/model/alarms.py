from dataclasses import dataclass,field
from typing import Any
@dataclass(slots=True)
class AlarmDefinition:
 alarm_id:str; name:str; tag_id:str|None=None; configuration:dict[str,Any]=field(default_factory=dict); metadata:dict[str,Any]=field(default_factory=dict)
