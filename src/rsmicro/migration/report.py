from dataclasses import asdict,dataclass,field
from typing import Any
@dataclass(slots=True)
class MigrationReport:
 source_file:str; output_file:str; source_format:str="plc-ascii-v1"; destination_format:str="rsmicro-project-v1"; objects_migrated:dict[str,int]=field(default_factory=dict); uuid_mapping_summary:dict[str,str]=field(default_factory=dict); aliases_normalized:list[dict[str,str]]=field(default_factory=list); warnings:list[dict[str,Any]]=field(default_factory=list); errors:list[dict[str,Any]]=field(default_factory=list); deployment_information:dict[str,Any]=field(default_factory=dict); unsupported_fields:list[str]=field(default_factory=list); semantic_differences:list[str]=field(default_factory=list)
 def to_dict(self): return asdict(self)
