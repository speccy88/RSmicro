from __future__ import annotations
from dataclasses import dataclass,field
from typing import Any
from .controller import Controller,ProducedTag,ConsumedTag
from .deployment import Deployment,Device,Endpoint,Binding
from .logic import Program,Routine,Rung,node_from_dict
from .scada import Scada
from .tags import Tag,TagType
@dataclass(slots=True)
class Project:
 project_id:str; name:str; description:str=""; controllers:list[Controller]=field(default_factory=list); deployments:list[Deployment]=field(default_factory=list); scada:Scada=field(default_factory=Scada); metadata:dict[str,Any]=field(default_factory=dict); format:str="rsmicro-project"; format_version:int=1
 def to_dict(self): return {"format":self.format,"format_version":self.format_version,"project_id":self.project_id,"name":self.name,"description":self.description,"controllers":[x.to_dict() for x in self.controllers],"deployments":[x.to_dict() for x in self.deployments],"scada":self.scada.to_dict(),"metadata":self.metadata}
 @classmethod
 def from_dict(cls,d):
  def tag(x): return Tag(x["tag_id"],x["name"],TagType(x["data_type"]),x.get("description",""),x.get("initial_value"),x.get("preset"),x.get("retentive",False),x.get("writable",True),dict(x.get("access",{})),x.get("engineering_unit"),x.get("minimum"),x.get("maximum"),x.get("scada_visible",True),dict(x.get("metadata",{})))
  def prog(x): return Program(x["program_id"],x["name"],[Routine(y["routine_id"],y["name"],[Rung(z["rung_id"],[node_from_dict(n) for n in z.get("nodes",[])],z.get("comment",""),dict(z.get("metadata",{}))) for z in y.get("rungs",[])],y.get("description",""),dict(y.get("metadata",{}))) for y in x.get("routines",[])],x.get("description",""),dict(x.get("metadata",{})))
  cs=[]
  for x in d.get("controllers",[]):
   ps=[ProducedTag(**y) for y in x.get("produced_tags",[])]; qs=[ConsumedTag(**y) for y in x.get("consumed_tags",[])]
   cs.append(Controller(x["controller_id"],x["name"],x.get("description",""),x.get("compatibility_profile"),[tag(y) for y in x.get("tags",[])],[prog(y) for y in x.get("programs",[])],dict(x.get("cyclic_task",{})),ps,qs,dict(x.get("metadata",{}))))
  ds=[]
  for x in d.get("deployments",[]):
   devs=[Device(y["device_id"],y["driver_type"],y.get("description",""),dict(y.get("properties",{})),[Endpoint(**z) for z in y.get("endpoints",[])]) for y in x.get("devices",[])]
   ds.append(Deployment(x["deployment_id"],x["name"],x["controller_id"],x["target_platform"],x.get("board_identifier"),dict(x.get("connection",{})),devs,[Binding(**y) for y in x.get("bindings",[])],dict(x.get("driver_configuration",{})),dict(x.get("metadata",{}))))
  s=d.get("scada",{})
  return cls(d["project_id"],d["name"],d.get("description",""),cs,ds,Scada(list(s.get("screens",[])),list(s.get("alarms",[])),dict(s.get("historian",{})),dict(s.get("metadata",{}))),dict(d.get("metadata",{})),d.get("format",""),d.get("format_version",0))
