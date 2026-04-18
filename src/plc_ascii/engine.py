from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias

from .model import Branch, Node, Program, Step, split_timer_member


@dataclass(slots=True)
class TimerState:
    pre: int
    acc: int = 0
    dn: bool = False
    en: bool = False
    tt: bool = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "pre": self.pre,
            "acc": self.acc,
            "dn": self.dn,
            "en": self.en,
            "tt": self.tt,
        }


@dataclass(slots=True)
class StepTrace:
    op: str
    tag: str
    arg: int | None
    power_in: bool
    truth: bool
    power_out: bool


@dataclass(slots=True)
class BranchTrace:
    power_in: bool
    power_out: bool
    lane_outputs: list[bool]
    lanes: list[list["NodeTrace"]]


NodeTrace: TypeAlias = StepTrace | BranchTrace


@dataclass(slots=True)
class ScanResult:
    scan_ms: int
    rung_power: list[bool]
    tags: dict[str, bool]
    timers: dict[str, dict[str, Any]]
    traces: list[list[NodeTrace]]


def _read_snapshot_tag(tag: str, tags: dict[str, bool], forced: dict[str, bool]) -> bool:
    if tag in forced:
        return bool(forced[tag])
    return bool(tags.get(tag, False))


def _trace_step(read_tag: Any, step: Step, power_in: bool) -> tuple[bool, StepTrace]:
    if step.op == "XIC":
        truth = read_tag(step.tag)
        return power_in and truth, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in and truth)
    if step.op == "XIO":
        truth = not read_tag(step.tag)
        return power_in and truth, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in and truth)
    truth = power_in
    return power_in, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in)


def _trace_nodes(read_tag: Any, nodes: list[Node], power_in: bool) -> tuple[bool, list[NodeTrace]]:
    current = power_in
    traces: list[NodeTrace] = []
    for node in nodes:
        current_in = current
        if isinstance(node, Step):
            current, trace = _trace_step(read_tag, node, current)
        else:
            lane_traces: list[list[NodeTrace]] = []
            lane_outputs: list[bool] = []
            for lane in node.lanes:
                lane_out, nested = _trace_nodes(read_tag, lane, current_in)
                lane_outputs.append(lane_out)
                lane_traces.append(nested)
            current = any(lane_outputs) if lane_outputs else current_in
            trace = BranchTrace(
                power_in=current_in,
                power_out=current,
                lane_outputs=lane_outputs,
                lanes=lane_traces,
            )
        traces.append(trace)
    return current, traces


def trace_program_state(
    program: Program,
    tags: dict[str, bool],
    forced: dict[str, bool] | None = None,
) -> tuple[list[bool], list[list[NodeTrace]]]:
    current_forced = forced or {}
    read_tag = lambda tag: _read_snapshot_tag(tag, tags, current_forced)
    rung_power: list[bool] = []
    traces: list[list[NodeTrace]] = []
    for rung in program.rungs:
        out, rung_traces = _trace_nodes(read_tag, rung.elements, True)
        rung_power.append(out)
        traces.append(rung_traces)
    return rung_power, traces


@dataclass(slots=True)
class LadderEngine:
    program: Program
    tags: dict[str, bool] = field(default_factory=dict)
    forced: dict[str, bool] = field(default_factory=dict)
    timers: dict[str, TimerState] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for timer in self.program.timer_configs().values():
            self.timers.setdefault(timer.tag, TimerState(pre=timer.preset_ms))

    def load_program(self, program: Program) -> None:
        self.program = program
        self.timers.clear()
        for timer in program.timer_configs().values():
            self.timers[timer.tag] = TimerState(pre=timer.preset_ms)

    def _sync_timer_tag(self, timer_name: str) -> None:
        timer = self.timers.get(timer_name)
        if timer is None:
            return
        self.tags[f"{timer_name}.en"] = timer.en
        self.tags[f"{timer_name}.dn"] = timer.dn
        self.tags[f"{timer_name}.tt"] = timer.tt

    def _sync_all_timer_tags(self) -> None:
        for timer_name in self.timers:
            self._sync_timer_tag(timer_name)

    def read_tag(self, tag: str) -> bool:
        if tag in self.forced:
            return self.forced[tag]
        timer_member = split_timer_member(tag)
        if timer_member is not None:
            timer_name, attr = timer_member
            timer = self.timers.get(timer_name)
            if timer is None:
                return False
            mapping = {"dn": timer.dn, "en": timer.en, "tt": timer.tt}
            return bool(mapping.get(attr, False))
        return bool(self.tags.get(tag, False))

    def write_tag(self, tag: str, value: bool) -> None:
        if tag in self.forced:
            self.tags[tag] = self.forced[tag]
            return
        self.tags[tag] = bool(value)

    def set_tag(self, tag: str, value: bool) -> None:
        self.tags[tag] = bool(value)

    def set_force(self, tag: str, value: bool) -> None:
        self.forced[tag] = bool(value)
        self.tags[tag] = bool(value)

    def clear_force(self, tag: str) -> None:
        self.forced.pop(tag, None)

    def reset_timers(self) -> None:
        for timer_name, timer in self.timers.items():
            timer.acc = 0
            timer.dn = False
            timer.en = False
            timer.tt = False
            self._sync_timer_tag(timer_name)

    def _execute_step(self, step: Step, power_in: bool, scan_ms: int) -> tuple[bool, StepTrace]:
        if step.op == "XIC":
            truth = self.read_tag(step.tag)
            power_out = power_in and truth
            return power_out, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_out)
        if step.op == "XIO":
            truth = not self.read_tag(step.tag)
            power_out = power_in and truth
            return power_out, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_out)
        if step.op == "OTE":
            self.write_tag(step.tag, power_in)
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)
        if step.op == "OTL":
            if power_in:
                self.write_tag(step.tag, True)
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)
        if step.op == "OTU":
            if power_in:
                self.write_tag(step.tag, False)
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)

        timer = self.timers.setdefault(step.tag, TimerState(pre=step.arg or 0))
        timer.en = power_in
        if power_in:
            timer.acc = min(timer.acc + scan_ms, timer.pre)
            timer.dn = timer.acc >= timer.pre
            timer.tt = not timer.dn
        else:
            timer.acc = 0
            timer.dn = False
            timer.tt = False
        self._sync_timer_tag(step.tag)
        return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)

    def _execute_nodes(self, nodes: list[Node], power_in: bool, scan_ms: int) -> tuple[bool, list[NodeTrace]]:
        current = power_in
        traces: list[NodeTrace] = []
        for node in nodes:
            current_in = current
            if isinstance(node, Step):
                current, trace = self._execute_step(node, current, scan_ms)
            else:
                lane_traces: list[list[NodeTrace]] = []
                lane_outputs: list[bool] = []
                for lane in node.lanes:
                    lane_out, nested = self._execute_nodes(lane, current_in, scan_ms)
                    lane_outputs.append(lane_out)
                    lane_traces.append(nested)
                current = any(lane_outputs) if lane_outputs else current_in
                trace = BranchTrace(
                    power_in=current_in,
                    power_out=current,
                    lane_outputs=lane_outputs,
                    lanes=lane_traces,
                )
            traces.append(trace)
        return current, traces

    def scan(self, scan_ms: int = 100) -> ScanResult:
        rung_power: list[bool] = []
        traces: list[list[NodeTrace]] = []
        for rung in self.program.rungs:
            power, rung_traces = self._execute_nodes(rung.elements, True, scan_ms)
            rung_power.append(power)
            traces.append(rung_traces)

        for tag, forced_value in self.forced.items():
            self.tags[tag] = forced_value
        self._sync_all_timer_tags()

        return ScanResult(
            scan_ms=scan_ms,
            rung_power=rung_power,
            tags=dict(sorted(self.tags.items())),
            timers={name: timer.snapshot() for name, timer in sorted(self.timers.items())},
            traces=traces,
        )

    def snapshot(self) -> dict[str, Any]:
        self._sync_all_timer_tags()
        rung_power, traces = trace_program_state(self.program, self.tags, self.forced)
        return {
            "program": self.program.to_dict(),
            "tags": dict(sorted(self.tags.items())),
            "forced": dict(sorted(self.forced.items())),
            "timers": {name: timer.snapshot() for name, timer in sorted(self.timers.items())},
            "rung_power": rung_power,
            "traces": traces,
        }
