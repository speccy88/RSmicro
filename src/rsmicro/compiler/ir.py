from dataclasses import dataclass
from typing import Any
@dataclass(frozen=True)
class IRTag: id:int; uuid:str; name:str; type:str; storage:str; initial:Any; retentive:bool
@dataclass(frozen=True)
class IROperand: kind:str; type:str; value:Any; member:str|None=None
@dataclass(frozen=True)
class IRInstruction: id:int; uuid:str; mnemonic:str; opcode:int; operands:tuple[IROperand,...]; state_slot:int|None; path:str
@dataclass(frozen=True)
class IRProgram: profile:str; abi:int; controller_uuid:str; tags:tuple[IRTag,...]; instructions:tuple[IRInstruction,...]; routines:tuple[dict,...]; rungs:tuple[dict,...]; branches:int; produced_tags:tuple[dict,...]=(); consumed_tags:tuple[dict,...]=()
