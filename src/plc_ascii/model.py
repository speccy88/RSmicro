from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias


VALID_CONTACTS = {"XIC", "XIO"}
VALID_ACTIONS = {"OTE", "OTL", "OTU", "TON"}
TIMER_CONTACT_MEMBERS = {"en", "dn", "tt"}


def split_timer_member(tag: str) -> tuple[str, str] | None:
    if "." not in tag:
        return None
    timer_name, member = tag.split(".", 1)
    return timer_name, member.lower()


@dataclass(slots=True)
class Step:
    op: str
    tag: str
    arg: int | None = None

    def validate(self) -> None:
        if self.op not in VALID_CONTACTS | VALID_ACTIONS:
            raise ValueError(f"Unsupported instruction: {self.op}")
        if not self.tag:
            raise ValueError("Instruction tag cannot be empty")
        timer_member = split_timer_member(self.tag)
        if self.op == "TON" and timer_member is not None:
            raise ValueError("TON must use a base timer tag, not a timer member")
        if self.op in {"OTE", "OTL", "OTU"} and timer_member is not None:
            raise ValueError("Output instructions cannot write timer members")
        if self.op in VALID_CONTACTS and timer_member is not None and timer_member[1] not in TIMER_CONTACT_MEMBERS:
            raise ValueError("XIC and XIO can only use timer members .en, .dn, or .tt")
        if self.op == "TON" and (self.arg is None or self.arg <= 0):
            raise ValueError("TON requires a positive preset in milliseconds")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"kind": "step", "op": self.op, "tag": self.tag}
        if self.arg is not None:
            payload["arg"] = self.arg
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Step":
        step = cls(
            op=str(payload["op"]).upper(),
            tag=str(payload["tag"]),
            arg=payload.get("arg"),
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
    address: str

    def validate(self) -> None:
        if self.direction not in {"input", "output"}:
            raise ValueError("Binding direction must be 'input' or 'output'")
        if not self.tag or not self.address:
            raise ValueError("Binding requires a tag and address")

    def to_dict(self) -> dict[str, str]:
        return {"tag": self.tag, "direction": self.direction, "address": self.address}

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Binding":
        binding = cls(
            tag=str(payload["tag"]),
            direction=str(payload["direction"]),
            address=str(payload["address"]),
        )
        binding.validate()
        return binding


@dataclass(slots=True)
class TimerConfig:
    tag: str
    preset_ms: int


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
    rungs: list[Rung] = field(default_factory=list)
    bindings: list[Binding] = field(default_factory=list)

    def validate(self) -> None:
        if not self.name:
            raise ValueError("Program name cannot be empty")
        for rung in self.rungs:
            rung.validate()
        for binding in self.bindings:
            binding.validate()

    def timer_configs(self) -> dict[str, TimerConfig]:
        timers: dict[str, TimerConfig] = {}
        for rung in self.rungs:
            for step in walk_steps(rung.elements):
                if step.op == "TON" and step.arg is not None:
                    timers[step.tag] = TimerConfig(tag=step.tag, preset_ms=step.arg)
        return timers

    def to_dict(self) -> dict[str, Any]:
        self.validate()
        return {
            "name": self.name,
            "rungs": [rung.to_dict() for rung in self.rungs],
            "bindings": [binding.to_dict() for binding in self.bindings],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "Program":
        program = cls(
            name=str(payload["name"]),
            rungs=[Rung.from_dict(rung_payload) for rung_payload in payload.get("rungs", [])],
            bindings=[Binding.from_dict(binding_payload) for binding_payload in payload.get("bindings", [])],
        )
        program.validate()
        return program
