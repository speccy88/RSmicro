from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, TypeAlias

@dataclass(slots=True)
class TagOperand:
    tag_id: str
    member: str | None = None
    def to_dict(self):
        d={"kind":"tag_member" if self.member else "tag","tag_id":self.tag_id}
        if self.member: d["member"]=self.member
        return d
@dataclass(slots=True)
class LiteralOperand:
    value: bool|int|float
    def to_dict(self): return {"kind": "literal", "value": self.value}
Operand: TypeAlias = TagOperand | LiteralOperand
@dataclass(slots=True)
class Instruction:
    instruction_id: str
    mnemonic: str
    operands: list[Operand]=field(default_factory=list)
    metadata: dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return {"node_type":"instruction","instruction_id":self.instruction_id,"mnemonic":self.mnemonic,"operands":[x.to_dict() for x in self.operands],"metadata":self.metadata}
@dataclass(slots=True)
class Branch:
    lanes: list[list["LogicNode"]]
    metadata: dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return {"node_type":"branch","lanes":[[node_to_dict(n) for n in lane] for lane in self.lanes],"metadata":self.metadata}
LogicNode: TypeAlias=Instruction|Branch
def node_to_dict(n: LogicNode): return n.to_dict()
def operand_from_dict(d): return TagOperand(d["tag_id"],d.get("member")) if d["kind"] in {"tag","tag_member"} else LiteralOperand(d["value"])
def node_from_dict(d):
    if d["node_type"]=="branch": return Branch([[node_from_dict(n) for n in lane] for lane in d["lanes"]],dict(d.get("metadata",{})))
    return Instruction(d["instruction_id"],d["mnemonic"],[operand_from_dict(x) for x in d.get("operands",[])],dict(d.get("metadata",{})))
@dataclass(slots=True)
class Rung:
    rung_id:str; nodes:list[LogicNode]=field(default_factory=list); comment:str=""; metadata:dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return {"rung_id":self.rung_id,"comment":self.comment,"nodes":[node_to_dict(n) for n in self.nodes],"metadata":self.metadata}
@dataclass(slots=True)
class Routine:
    routine_id:str; name:str; rungs:list[Rung]=field(default_factory=list); description:str=""; metadata:dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return {"routine_id":self.routine_id,"name":self.name,"description":self.description,"rungs":[r.to_dict() for r in self.rungs],"metadata":self.metadata}
@dataclass(slots=True)
class Program:
    program_id:str; name:str; routines:list[Routine]=field(default_factory=list); description:str=""; metadata:dict[str,Any]=field(default_factory=dict)
    def to_dict(self): return {"program_id":self.program_id,"name":self.name,"description":self.description,"routines":[r.to_dict() for r in self.routines],"metadata":self.metadata}
