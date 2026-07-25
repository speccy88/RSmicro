from dataclasses import dataclass
import hashlib
from typing import Any
from .diagnostics import CompilerDiagnostic as D
from .validation import validate_controller
from .lowering import lower
from .image import VERSION as IMAGE_FORMAT_VERSION,build
from .generated_opcodes import INSTRUCTION_ABI,PROFILE_ID,PROFILE_VERSION
@dataclass(frozen=True)
class CompileOptions: warnings_as_errors:bool=False; strip_debug:bool=False
@dataclass
class CompileResult:
 success:bool; diagnostics:list[D]; ir:Any=None; image_bytes:bytes|None=None; manifest:dict|None=None; debug_map:dict|None=None; hashes:dict|None=None; memory_estimates:dict|None=None
def compile_project(project,controller_id,profile=PROFILE_ID,deployment_id=None,options=None):
 options=options or CompileOptions()
 if profile!=PROFILE_ID: return CompileResult(False,[D('ERROR','RSM-E100',f'unsupported profile {profile}')])
 matches=[c for c in project.controllers if c.controller_id==controller_id or c.name==controller_id]
 if len(matches)!=1: return CompileResult(False,[D('ERROR','RSM-E103','controller is missing or ambiguous')])
 c=matches[0]; deps=[d for d in project.deployments if deployment_id and (d.deployment_id==deployment_id or d.name==deployment_id)]
 if deployment_id and len(deps)!=1: return CompileResult(False,[D('ERROR','RSM-E112','deployment is missing or ambiguous')])
 ds=validate_controller(c)
 if any(x.severity=='ERROR' for x in ds) or (options.warnings_as_errors and any(x.severity=='WARNING' for x in ds)): return CompileResult(False,ds)
 ir=lower(c,deps[0] if deps else None); image,dbg,mem,crc=build(ir,options.strip_debug); sha=hashlib.sha256(image).hexdigest()
 opcode_usage={}
 for i in ir.instructions: opcode_usage[i.mnemonic]=opcode_usage.get(i.mnemonic,0)+1
 manifest={'source_project_format':project.format,'source_project_format_version':project.format_version,'project_uuid':project.project_id,'controller_uuid':c.controller_id,'controller_name':c.name,'profile':PROFILE_ID,'profile_version':PROFILE_VERSION,'instruction_abi':INSTRUCTION_ABI,'image_format':'.'.join(map(str,IMAGE_FORMAT_VERSION)),'compiler_version':'0.1.0','image_size':len(image),'image_sha256':sha,'crc32':f'{crc:08x}','tag_count':len(ir.tags),'instruction_count':len(ir.instructions),'rung_count':len(ir.rungs),'routine_count':len(ir.routines),'state_slot_count':sum(i.state_slot is not None for i in ir.instructions),'required_capabilities':['SERIAL_LOGIC','PARALLEL_BRANCH','MONOTONIC_CLOCK','FORCES'],'required_data_types':sorted({t.type for t in ir.tags}),'opcode_usage':dict(sorted(opcode_usage.items())),'memory_estimates':mem,'warnings':[x.to_dict() for x in ds if x.severity=='WARNING'],'output_safe_state_validation':{'status':'not bound or validated by logical compiler'},'produced_tags':[],'consumed_tags':[]}
 return CompileResult(True,ds,ir,image,manifest,dbg,{'sha256':sha,'crc32':f'{crc:08x}'},mem)
