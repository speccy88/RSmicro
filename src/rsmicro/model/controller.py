from dataclasses import dataclass,field
from typing import Any
from .tags import Tag
from .logic import Program
@dataclass(slots=True)
class ProducedTag:
 produced_tag_id:str; source_tag_id:str; publish_name:str; update_policy:dict[str,Any]=field(default_factory=dict); description:str=""
 def to_dict(self): return {"produced_tag_id":self.produced_tag_id,"source_tag_id":self.source_tag_id,"publish_name":self.publish_name,"update_policy":self.update_policy,"description":self.description}
@dataclass(slots=True)
class ConsumedTag:
 consumed_tag_id:str; destination_tag_id:str; source_controller_id:str; source_produced_tag_id:str; expected_update_interval_ms:int|None=None; timeout_ms:int|None=None; stale_behavior:str="hold"; hold_last_value:bool=True; substitute_value:Any=None; quality_handling:dict[str,Any]=field(default_factory=dict)
 def to_dict(self): return {"consumed_tag_id":self.consumed_tag_id,"destination_tag_id":self.destination_tag_id,"source_controller_id":self.source_controller_id,"source_produced_tag_id":self.source_produced_tag_id,"expected_update_interval_ms":self.expected_update_interval_ms,"timeout_ms":self.timeout_ms,"stale_behavior":self.stale_behavior,"hold_last_value":self.hold_last_value,"substitute_value":self.substitute_value,"quality_handling":self.quality_handling}
@dataclass(slots=True)
class Controller:
 controller_id:str; name:str; description:str=""; compatibility_profile:str|None=None; tags:list[Tag]=field(default_factory=list); programs:list[Program]=field(default_factory=list); cyclic_task:dict[str,Any]=field(default_factory=lambda:{"name":"MainTask","program_order":[]}); produced_tags:list[ProducedTag]=field(default_factory=list); consumed_tags:list[ConsumedTag]=field(default_factory=list); metadata:dict[str,Any]=field(default_factory=dict)
 def to_dict(self): return {"controller_id":self.controller_id,"name":self.name,"description":self.description,"compatibility_profile":self.compatibility_profile,"tags":[x.to_dict() for x in self.tags],"programs":[x.to_dict() for x in self.programs],"cyclic_task":self.cyclic_task,"produced_tags":[x.to_dict() for x in self.produced_tags],"consumed_tags":[x.to_dict() for x in self.consumed_tags],"metadata":self.metadata}
