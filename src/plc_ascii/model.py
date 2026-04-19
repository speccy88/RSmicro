from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias


Operand: TypeAlias = str | int | float
ScalarValue: TypeAlias = bool | int | float
BindingAddress: TypeAlias = str | int


VALID_CONTACTS = {"XIC", "XIO", "CMP", "EQ", "GT", "GTE", "LT", "LE", "NE"}
VALID_ACTIONS = {"OTE", "OTL", "OTU", "TON", "CTU", "CTD", "MOV", "CLR", "ADD", "ABS", "MUL", "DIV", "NEG", "SUB"}
TIMER_CONTACT_MEMBERS = {"en", "dn", "tt"}
VARIABLE_TYPES = {"bool", "int", "float", "timer", "counter"}
RUNTIME_TARGET_CIRCUITPYTHON = "circuitpython"
RUNTIME_TARGET_MICROPYTHON = "micropython"
RUNTIME_TARGET_PROPELLER2 = "propeller2"
VALID_RUNTIME_TARGETS = {RUNTIME_TARGET_CIRCUITPYTHON, RUNTIME_TARGET_MICROPYTHON, RUNTIME_TARGET_PROPELLER2}
COMPARE_SYMBOLS = {
    "CMP": "==",
    "EQ": "==",
    "NE": "!=",
    "GT": ">",
    "GTE": ">=",
    "LT": "<",
    "LE": "<=",
}
SINGLE_TAG_OPS = {"XIC", "XIO", "OTE", "OTL", "OTU", "TON", "CTU", "CTD", "CLR"}
UNARY_SOURCE_OPS = {"MOV", "ABS", "NEG"}
BINARY_SOURCE_OPS = {"ADD", "SUB", "MUL", "DIV"}
WRITE_TAG_OPS = {"OTE", "OTL", "OTU", "TON", "CTU", "CTD", "MOV", "CLR", "ADD", "ABS", "NEG", "SUB", "MUL", "DIV"}


def normalize_runtime_target(value: Any) -> str:
    text = str(value or RUNTIME_TARGET_CIRCUITPYTHON).strip().lower()
    if text in {"propeller2", "propeller2-taqoz", "taqoz"}:
        return RUNTIME_TARGET_PROPELLER2
    if text in {"micropython", "micro-python"}:
        return RUNTIME_TARGET_MICROPYTHON
    if text in VALID_RUNTIME_TARGETS:
        return text
    return RUNTIME_TARGET_CIRCUITPYTHON


def split_timer_member(tag: str) -> tuple[str, str] | None:
    if "." not in tag:
        return None
    timer_name, member = tag.split(".", 1)
    return timer_name, member.lower()


def normalize_operand(value: Any) -> Operand:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text:
        raise ValueError("Operand cannot be empty")
    return text


def operand_is_tag(value: Operand) -> bool:
    return isinstance(value, str)


def format_operand(value: Operand) -> str:
    if isinstance(value, float):
        return format(value, "g")
    return str(value)


def step_compare_operator(step: "Step") -> str | None:
    if step.op not in COMPARE_SYMBOLS:
        return None
    if step.op == "CMP":
        operator = str(step.params.get("cmp", "")).strip()
        if operator not in {"==", "!=", ">", ">=", "<", "<="}:
            raise ValueError("CMP requires a valid comparison operator")
        return operator
    return COMPARE_SYMBOLS[step.op]


def step_primary_tag(step: "Step") -> str | None:
    if step.tag:
        return step.tag
    for key in ("dest", "source", "left", "right"):
        value = step.params.get(key)
        if isinstance(value, str):
            return value
    return None


def step_is_contact(step: "Step") -> bool:
    return step.op in VALID_CONTACTS


@dataclass(slots=True)
class Variable:
    tag: str
    data_type: str
    initial: ScalarValue | None = None
    preset: int | None = None

    def validate(self) -> None:
        self.tag = self.tag.strip()
        self.data_type = self.data_type.strip().lower()
        if not self.tag:
            raise ValueError("Variable tag cannot be empty")
        if self.data_type not in VARIABLE_TYPES:
            raise ValueError(f"Unsupported variable type: {self.data_type}")
        if self.data_type == "bool":
            self.initial = bool(self.initial)
            self.preset = None
            return
        if self.data_type == "int":
            self.initial = int(self.initial or 0)
            self.preset = None
            return
        if self.data_type == "float":
            self.initial = float(self.initial or 0.0)
            self.preset = None
            return
        self.initial = None
        self.preset = int(self.preset or 0)

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        payload: dict[str, Any] = {"tag": self.tag, "type": self.data_type}
        if self.initial is not None:
            payload["initial"] = self.initial
        if self.preset is not None:
            payload["preset"] = self.preset
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Variable":
        variable = cls(
            tag=str(payload["tag"]),
            data_type=str(payload.get("type", payload.get("data_type", ""))),
            initial=payload.get("initial"),
            preset=payload.get("preset"),
        )
        variable.validate()
        return variable


@dataclass(slots=True)
class Step:
    op: str
    tag: str = ""
    arg: int | None = None
    params: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        self.op = self.op.upper().strip()
        self.tag = self.tag.strip()
        self.params = dict(self.params)

        if self.op not in VALID_CONTACTS | VALID_ACTIONS:
            raise ValueError(f"Unsupported instruction: {self.op}")
        if self.op in SINGLE_TAG_OPS and not self.tag:
            raise ValueError("Instruction tag cannot be empty")

        timer_member = split_timer_member(self.tag) if self.tag else None
        if self.op == "TON" and timer_member is not None:
            raise ValueError("TON must use a base timer tag, not a timer member")
        if self.op in WRITE_TAG_OPS and timer_member is not None:
            raise ValueError("Output instructions cannot write timer members")
        if self.op in {"XIC", "XIO"} and timer_member is not None and timer_member[1] not in TIMER_CONTACT_MEMBERS:
            raise ValueError("XIC and XIO can only use timer members .en, .dn, or .tt")
        if self.op == "TON" and (self.arg is None or self.arg <= 0):
            raise ValueError("TON requires a positive preset in milliseconds")
        if self.op in {"CTU", "CTD"} and self.arg is not None and self.arg < 0:
            raise ValueError("Counter preset cannot be negative")
        if self.op in {"TON", "CTU", "CTD"}:
            self.params.clear()
            return

        if self.op in {"XIC", "XIO", "OTE", "OTL", "OTU", "CLR"}:
            self.params.clear()
            return

        if self.op in {"CMP", "EQ", "GT", "GTE", "LT", "LE", "NE"}:
            left = normalize_operand(self.params.get("left", ""))
            right = normalize_operand(self.params.get("right", ""))
            if self.op == "CMP":
                operator = step_compare_operator(self)
                assert operator is not None
                self.params = {"left": left, "right": right, "cmp": operator}
            else:
                self.params = {"left": left, "right": right}
            return

        if self.op in UNARY_SOURCE_OPS:
            if not self.tag:
                raise ValueError(f"{self.op} requires a destination tag")
            if split_timer_member(self.tag) is not None:
                raise ValueError(f"{self.op} cannot write timer members")
            source = normalize_operand(self.params.get("source", ""))
            self.params = {"source": source}
            return

        if self.op in BINARY_SOURCE_OPS:
            if not self.tag:
                raise ValueError(f"{self.op} requires a destination tag")
            if split_timer_member(self.tag) is not None:
                raise ValueError(f"{self.op} cannot write timer members")
            left = normalize_operand(self.params.get("left", ""))
            right = normalize_operand(self.params.get("right", ""))
            self.params = {"left": left, "right": right}
            return

        raise ValueError(f"Instruction validation not implemented for {self.op}")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": "step", "op": self.op}
        if self.tag:
            payload["tag"] = self.tag
        if self.arg is not None:
            payload["arg"] = self.arg
        if self.params:
            payload["params"] = self.params
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Step":
        step = cls(
            op=str(payload["op"]).upper(),
            tag=str(payload.get("tag", "")),
            arg=payload.get("arg"),
            params=dict(payload.get("params", {})),
        )
        step.validate()
        return step


@dataclass(slots=True)
class Branch:
    lanes: list[list["Node"]] = field(default_factory=lambda: [[], []])

    def validate(self) -> None:
        if len(self.lanes) < 2:
            raise ValueError("A branch requires at least two lanes")
        for lane in self.lanes:
            for node in lane:
                validate_node(node)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "branch",
            "lanes": [[node_to_dict(node) for node in lane] for lane in self.lanes],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Branch":
        branch = cls(
            lanes=[
                [node_from_dict(node_payload) for node_payload in lane_payload]
                for lane_payload in payload.get("lanes", [])
            ]
        )
        branch.validate()
        return branch


Node: TypeAlias = Step | Branch


def validate_node(node: Node) -> None:
    if isinstance(node, Step):
        node.validate()
        return
    node.validate()


def node_to_dict(node: Node) -> dict[str, Any]:
    if isinstance(node, Step):
        return node.to_dict()
    return node.to_dict()


def node_from_dict(payload: dict[str, Any]) -> Node:
    kind = str(payload.get("kind", "step")).lower()
    if kind == "branch":
        return Branch.from_dict(payload)
    return Step.from_dict(payload)


def walk_steps(nodes: list[Node]) -> list[Step]:
    steps: list[Step] = []
    for node in nodes:
        if isinstance(node, Step):
            steps.append(node)
        else:
            for lane in node.lanes:
                steps.extend(walk_steps(lane))
    return steps


@dataclass(slots=True)
class Binding:
    tag: str
    direction: str
    address: BindingAddress

    def validate(self) -> None:
        if self.direction not in {"input", "output"}:
            raise ValueError("Binding direction must be 'input' or 'output'")
        if not self.tag:
            raise ValueError("Binding requires a tag and address")
        if isinstance(self.address, str):
            self.address = self.address.strip()
            if not self.address:
                raise ValueError("Binding requires a tag and address")
        elif not isinstance(self.address, int):
            raise ValueError("Binding address must be a string or integer")

    def to_dict(self) -> dict[str, BindingAddress]:
        return {"tag": self.tag, "direction": self.direction, "address": self.address}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Binding":
        raw_address = payload["address"]
        binding = cls(
            tag=str(payload["tag"]),
            direction=str(payload["direction"]),
            address=raw_address if isinstance(raw_address, int) else str(raw_address),
        )
        binding.validate()
        return binding


@dataclass(slots=True)
class TimerConfig:
    tag: str
    preset_ms: int


@dataclass(slots=True)
class CounterConfig:
    tag: str
    preset: int


@dataclass(slots=True)
class Rung:
    name: str = ""
    comment: str = ""
    elements: list[Node] = field(default_factory=list)
    conditions: list[Step] = field(default_factory=list, repr=False)
    actions: list[Step] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if not self.elements and (self.conditions or self.actions):
            self.elements = [*self.conditions, *self.actions]

    def validate(self) -> None:
        for node in self.elements:
            validate_node(node)

    def to_dict(self) -> dict[str, Any]:
        return {
            "comment": self.comment,
            "elements": [node_to_dict(node) for node in self.elements],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Rung":
        if "elements" in payload:
            rung = cls(
                comment=str(payload.get("comment", "")),
                elements=[node_from_dict(node_payload) for node_payload in payload.get("elements", [])],
            )
            rung.validate()
            return rung

        rung = cls(
            name=str(payload.get("name", "")),
            comment=str(payload.get("comment", "")),
            conditions=[Step.from_dict(step) for step in payload.get("conditions", [])],
            actions=[Step.from_dict(step) for step in payload.get("actions", [])],
        )
        rung.validate()
        return rung


@dataclass(slots=True)
class Program:
    name: str
    runtime_target: str = RUNTIME_TARGET_CIRCUITPYTHON
    rungs: list[Rung] = field(default_factory=list)
    variables: list[Variable] = field(default_factory=list)
    bindings: list[Binding] = field(default_factory=list)

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Program name cannot be empty")
        self.runtime_target = normalize_runtime_target(self.runtime_target)
        for rung in self.rungs:
            rung.validate()
        seen: set[str] = set()
        for variable in self.variables:
            variable.validate()
            if variable.tag in seen:
                raise ValueError(f"Duplicate variable declaration: {variable.tag}")
            seen.add(variable.tag)
        for binding in self.bindings:
            binding.validate()

    def variable_map(self) -> dict[str, Variable]:
        return {variable.tag: variable for variable in self.variables}

    def timer_configs(self) -> dict[str, TimerConfig]:
        timers: dict[str, TimerConfig] = {}
        variable_map = self.variable_map()
        for variable in self.variables:
            if variable.data_type == "timer":
                timers[variable.tag] = TimerConfig(tag=variable.tag, preset_ms=int(variable.preset or 0))
        for rung in self.rungs:
            for step in walk_steps(rung.elements):
                if step.op == "TON" and step.arg is not None:
                    preset = variable_map.get(step.tag).preset if step.tag in variable_map and variable_map[step.tag].data_type == "timer" else step.arg
                    timers[step.tag] = TimerConfig(tag=step.tag, preset_ms=int(preset or 0))
        return timers

    def counter_configs(self) -> dict[str, CounterConfig]:
        counters: dict[str, CounterConfig] = {}
        variable_map = self.variable_map()
        for variable in self.variables:
            if variable.data_type == "counter":
                counters[variable.tag] = CounterConfig(tag=variable.tag, preset=int(variable.preset or 0))
        for rung in self.rungs:
            for step in walk_steps(rung.elements):
                if step.op in {"CTU", "CTD"} and step.tag:
                    preset = (
                        variable_map.get(step.tag).preset
                        if step.tag in variable_map and variable_map[step.tag].data_type == "counter"
                        else step.arg
                    )
                    counters.setdefault(step.tag, CounterConfig(tag=step.tag, preset=int(preset or 0)))
        return counters

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "name": self.name,
            "runtime_target": self.runtime_target,
            "rungs": [rung.to_dict() for rung in self.rungs],
            "variables": [variable.to_dict() for variable in self.variables],
            "bindings": [binding.to_dict() for binding in self.bindings],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Program":
        program = cls(
            name=str(payload["name"]),
            runtime_target=normalize_runtime_target(payload.get("runtime_target")),
            rungs=[Rung.from_dict(rung_payload) for rung_payload in payload.get("rungs", [])],
            variables=[Variable.from_dict(variable_payload) for variable_payload in payload.get("variables", [])],
            bindings=[Binding.from_dict(binding_payload) for binding_payload in payload.get("bindings", [])],
        )
        program.validate()
        return program
