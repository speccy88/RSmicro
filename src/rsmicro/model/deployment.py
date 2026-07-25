from dataclasses import dataclass,field
from typing import Any
@dataclass(slots=True)
class Endpoint:
 endpoint_id:str; direction:str; data_type:str; address:str|int; readable:bool=True; writable:bool=False; safe_value:Any=None; active_low:bool|None=None; quality:dict[str,Any]=field(default_factory=dict); metadata:dict[str,Any]=field(default_factory=dict)
 def to_dict(self): return self.__dict__ if hasattr(self,'__dict__') else {k:getattr(self,k) for k in self.__slots__}
@dataclass(slots=True)
class Device:
 device_id:str; driver_type:str; description:str=""; properties:dict[str,Any]=field(default_factory=dict); endpoints:list[Endpoint]=field(default_factory=list)
 def to_dict(self): return {"device_id":self.device_id,"driver_type":self.driver_type,"description":self.description,"properties":self.properties,"endpoints":[x.to_dict() for x in self.endpoints]}
@dataclass(slots=True)
class Binding:
 binding_id:str; tag_id:str; device_id:str; endpoint_id:str; metadata:dict[str,Any]=field(default_factory=dict)
 def to_dict(self): return {"binding_id":self.binding_id,"tag_id":self.tag_id,"device_id":self.device_id,"endpoint_id":self.endpoint_id,"metadata":self.metadata}
@dataclass(slots=True)
class Deployment:
 deployment_id:str; name:str; controller_id:str; target_platform:str; board_identifier:str|None=None; connection:dict[str,Any]=field(default_factory=dict); devices:list[Device]=field(default_factory=list); bindings:list[Binding]=field(default_factory=list); driver_configuration:dict[str,Any]=field(default_factory=dict); metadata:dict[str,Any]=field(default_factory=dict)
 def to_dict(self): return {"deployment_id":self.deployment_id,"name":self.name,"controller_id":self.controller_id,"target_platform":self.target_platform,"board_identifier":self.board_identifier,"connection":self.connection,"devices":[x.to_dict() for x in self.devices],"bindings":[x.to_dict() for x in self.bindings],"driver_configuration":self.driver_configuration,"metadata":self.metadata}
