from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TypeAlias

from .model import Branch, Node, Operand, Program, ScalarValue, Step, Variable, split_timer_member, step_compare_operator


TagValue: TypeAlias = bool | int | float


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
class CounterState:
    pre: int = 0
    acc: int = 0
    dn: bool = False

    def snapshot(self) -> dict[str, Any]:
        return {
            "pre": self.pre,
            "acc": self.acc,
            "dn": self.dn,
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
    tags: dict[str, TagValue]
    timers: dict[str, dict[str, Any]]
    counters: dict[str, dict[str, Any]]
    traces: list[list[NodeTrace]]


def _read_snapshot_tag(tag: str, tags: dict[str, TagValue], forced: dict[str, TagValue]) -> TagValue:
    if tag in forced:
        return forced[tag]
    timer_member = split_timer_member(tag)
    if timer_member is not None:
        _, attr = timer_member
        if tag in tags:
            return tags[tag]
        base = tags.get(tag, False)
        if isinstance(base, dict):
            return base.get(attr, False)
    return tags.get(tag, False)


def _coerce_truth(value: TagValue) -> bool:
    return bool(value)


def _apply_compare(left: TagValue, right: TagValue, operator: str) -> bool:
    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right
    if operator == ">":
        return left > right
    if operator == ">=":
        return left >= right
    if operator == "<":
        return left < right
    if operator == "<=":
        return left <= right
    raise ValueError(f"Unsupported comparison operator {operator}")


def _resolve_step_operand(read_value: Any, operand: Operand) -> TagValue:
    if isinstance(operand, str):
        return read_value(operand)
    return operand


def _binary_numeric_result(left: TagValue, right: TagValue, op: str) -> TagValue:
    if op == "ADD":
        return left + right
    if op == "SUB":
        return left - right
    if op == "MUL":
        return left * right
    if op == "DIV":
        return left / right
    raise ValueError(f"Unsupported numeric instruction {op}")


def _trace_step(read_tag: Any, step: Step, power_in: bool) -> tuple[bool, StepTrace]:
    if step.op == "XIC":
        truth = _coerce_truth(read_tag(step.tag))
        return power_in and truth, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in and truth)
    if step.op == "XIO":
        truth = not _coerce_truth(read_tag(step.tag))
        return power_in and truth, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in and truth)
    if step_compare_operator(step) is not None:
        left = _resolve_step_operand(read_tag, step.params["left"])
        right = _resolve_step_operand(read_tag, step.params["right"])
        truth = _apply_compare(left, right, step_compare_operator(step) or "==")
        return power_in and truth, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in and truth)
    if step.op in {"OTE", "OTL", "OTU", "MOV", "CLR", "ABS", "NEG", "ADD", "SUB", "MUL", "DIV"}:
        truth = _coerce_truth(read_tag(step.tag))
        return power_in, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in)
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
    tags: dict[str, TagValue],
    forced: dict[str, TagValue] | None = None,
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


def trace_program_preview(
    program: Program,
    tags: dict[str, TagValue],
    forced: dict[str, TagValue] | None = None,
    timer_values: dict[str, dict[str, Any]] | None = None,
    counter_values: dict[str, dict[str, Any]] | None = None,
) -> tuple[list[bool], list[list[NodeTrace]]]:
    current_forced = forced or {}
    timer_values = timer_values or {}
    counter_values = counter_values or {}

    def read_tag(tag: str) -> TagValue:
        if tag in current_forced:
            return current_forced[tag]
        timer_member = split_timer_member(tag)
        if timer_member is not None:
            base, attr = timer_member
            timer = timer_values.get(base)
            if isinstance(timer, dict):
                return timer.get(attr, False)
            counter = counter_values.get(base)
            if isinstance(counter, dict):
                return counter.get(attr, False)
        return tags.get(tag, False)

    def preview_step(step: Step) -> StepTrace:
        operator = step_compare_operator(step)
        if step.op == "XIC":
            truth = _coerce_truth(read_tag(step.tag))
        elif step.op == "XIO":
            truth = not _coerce_truth(read_tag(step.tag))
        elif operator is not None:
            left = _resolve_step_operand(read_tag, step.params["left"])
            right = _resolve_step_operand(read_tag, step.params["right"])
            truth = _apply_compare(left, right, operator)
        elif step.op in {"OTE", "OTL", "OTU", "MOV", "CLR", "ADD", "ABS", "MUL", "DIV", "NEG", "SUB"}:
            truth = _coerce_truth(read_tag(step.tag))
        elif step.op == "TON":
            timer = timer_values.get(step.tag, {})
            truth = bool(timer.get("en") or timer.get("dn") or timer.get("tt") or timer.get("acc"))
        elif step.op in {"CTU", "CTD"}:
            counter = counter_values.get(step.tag, {})
            truth = bool(counter.get("dn") or counter.get("acc"))
        else:
            truth = False
        return StepTrace(step.op, step.tag, step.arg, False, truth, False)

    def preview_nodes(nodes: list[Node]) -> list[NodeTrace]:
        traces: list[NodeTrace] = []
        for node in nodes:
            if isinstance(node, Step):
                traces.append(preview_step(node))
                continue
            lane_traces = [preview_nodes(lane) for lane in node.lanes]
            traces.append(BranchTrace(power_in=False, power_out=False, lane_outputs=[False for _ in node.lanes], lanes=lane_traces))
        return traces

    rung_power = [False for _ in program.rungs]
    traces = [preview_nodes(rung.elements) for rung in program.rungs]
    return rung_power, traces


@dataclass(slots=True)
class LadderEngine:
    program: Program
    tags: dict[str, TagValue] = field(default_factory=dict)
    forced: dict[str, TagValue] = field(default_factory=dict)
    timers: dict[str, TimerState] = field(default_factory=dict)
    counters: dict[str, CounterState] = field(default_factory=dict)
    edge_memory: dict[str, bool] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.restore_initial_values(clear_forces=False)

    def load_program(self, program: Program) -> None:
        current_tags = dict(self.tags)
        current_forced = dict(self.forced)
        current_timers = {name: TimerState(**timer.snapshot()) for name, timer in self.timers.items()}
        current_counters = {name: CounterState(**counter.snapshot()) for name, counter in self.counters.items()}
        self.program = program
        self.tags = {}
        self.forced = current_forced
        self.timers = {}
        self.counters = {}
        self.edge_memory = {}

        variable_map = self.program.variable_map()
        for variable in self.program.variables:
            if variable.data_type in {"bool", "int", "float"}:
                self.tags[variable.tag] = current_tags.get(variable.tag, variable.initial if variable.initial is not None else 0)

        for timer in program.timer_configs().values():
            existing = current_timers.get(timer.tag)
            if existing is not None:
                existing.pre = int(variable_map.get(timer.tag).preset) if timer.tag in variable_map and variable_map[timer.tag].data_type == "timer" else existing.pre
                self.timers[timer.tag] = existing
            else:
                self.timers[timer.tag] = TimerState(pre=timer.preset_ms)

        for counter in program.counter_configs().values():
            existing_counter = current_counters.get(counter.tag)
            if existing_counter is not None:
                existing_counter.pre = int(variable_map.get(counter.tag).preset) if counter.tag in variable_map and variable_map[counter.tag].data_type == "counter" else existing_counter.pre
                self.counters[counter.tag] = existing_counter
            else:
                self.counters[counter.tag] = CounterState(pre=counter.preset)

        self._sync_all_timer_tags()
        self._sync_all_counter_tags()

    def restore_initial_values(self, clear_forces: bool = False) -> None:
        self.tags.clear()
        if clear_forces:
            self.forced.clear()
        self.edge_memory.clear()
        for variable in self.program.variables:
            if variable.data_type in {"bool", "int", "float"}:
                self.tags[variable.tag] = variable.initial if variable.initial is not None else 0

        self.timers.clear()
        for timer in self.program.timer_configs().values():
            self.timers[timer.tag] = TimerState(pre=timer.preset_ms)
        self.counters.clear()
        for counter in self.program.counter_configs().values():
            self.counters[counter.tag] = CounterState(pre=counter.preset)
        self._sync_all_timer_tags()
        self._sync_all_counter_tags()

    def _sync_timer_tag(self, timer_name: str) -> None:
        timer = self.timers.get(timer_name)
        if timer is None:
            return
        self.tags[f"{timer_name}.pre"] = timer.pre
        self.tags[f"{timer_name}.acc"] = timer.acc
        self.tags[f"{timer_name}.en"] = timer.en
        self.tags[f"{timer_name}.dn"] = timer.dn
        self.tags[f"{timer_name}.tt"] = timer.tt

    def _sync_all_timer_tags(self) -> None:
        for timer_name in self.timers:
            self._sync_timer_tag(timer_name)

    def _sync_counter_tag(self, counter_name: str) -> None:
        counter = self.counters.get(counter_name)
        if counter is None:
            return
        self.tags[f"{counter_name}.pre"] = counter.pre
        self.tags[f"{counter_name}.acc"] = counter.acc
        self.tags[f"{counter_name}.dn"] = counter.dn

    def _sync_all_counter_tags(self) -> None:
        for counter_name in self.counters:
            self._sync_counter_tag(counter_name)

    def read_tag(self, tag: str) -> TagValue:
        if tag in self.forced:
            return self.forced[tag]
        timer_member = split_timer_member(tag)
        if timer_member is not None:
            timer_name, attr = timer_member
            timer = self.timers.get(timer_name)
            if timer is not None:
                mapping: dict[str, TagValue] = {
                    "dn": timer.dn,
                    "en": timer.en,
                    "tt": timer.tt,
                    "acc": timer.acc,
                    "pre": timer.pre,
                }
                return mapping.get(attr, False)
            counter = self.counters.get(timer_name)
            if counter is not None:
                mapping = {
                    "dn": counter.dn,
                    "acc": counter.acc,
                    "pre": counter.pre,
                }
                return mapping.get(attr, False)
        return self.tags.get(tag, False)

    def resolve_operand(self, operand: Operand) -> TagValue:
        if isinstance(operand, str):
            return self.read_tag(operand)
        return operand

    def write_tag(self, tag: str, value: TagValue) -> None:
        if tag in self.forced:
            self.tags[tag] = self.forced[tag]
            return
        self.tags[tag] = value

    def set_tag(self, tag: str, value: TagValue) -> None:
        self.tags[tag] = value

    def set_force(self, tag: str, value: TagValue) -> None:
        self.forced[tag] = value
        self.tags[tag] = value

    def clear_force(self, tag: str) -> None:
        self.forced.pop(tag, None)

    def clear_boolean_values(self) -> None:
        for variable in self.program.variables:
            if variable.data_type == "bool":
                self.tags[variable.tag] = False

    def stop_offline(self, *, reset_numeric: bool, clear_forces: bool) -> None:
        retained_forces = {} if clear_forces else dict(self.forced)
        if clear_forces:
            self.forced.clear()

        self.edge_memory.clear()

        for variable in self.program.variables:
            if variable.data_type == "bool":
                self.tags[variable.tag] = False
            elif variable.data_type == "int":
                if reset_numeric:
                    self.tags[variable.tag] = 0
                else:
                    self.tags[variable.tag] = int(self.tags.get(variable.tag, variable.initial if variable.initial is not None else 0))
            elif variable.data_type == "float":
                if reset_numeric:
                    self.tags[variable.tag] = 0.0
                else:
                    self.tags[variable.tag] = float(self.tags.get(variable.tag, variable.initial if variable.initial is not None else 0.0))

        for timer_name, timer in self.timers.items():
            timer.acc = 0
            timer.dn = False
            timer.en = False
            timer.tt = False
            self._sync_timer_tag(timer_name)

        for counter_name, counter in self.counters.items():
            counter.acc = 0
            counter.dn = False
            self._sync_counter_tag(counter_name)

        for tag, value in retained_forces.items():
            self.tags[tag] = value

    def reset_timers(self) -> None:
        for timer_name, timer in self.timers.items():
            timer.acc = 0
            timer.dn = False
            timer.en = False
            timer.tt = False
            self._sync_timer_tag(timer_name)

    def reset_counters(self) -> None:
        for counter_name, counter in self.counters.items():
            counter.acc = 0
            counter.dn = False
            self._sync_counter_tag(counter_name)
        self.edge_memory.clear()

    def reset_runtime(self, clear_forces: bool = False) -> None:
        self.restore_initial_values(clear_forces=clear_forces)

    def set_value(self, tag: str, value: TagValue) -> None:
        timer_member = split_timer_member(tag)
        if timer_member is not None:
            base_tag, member = timer_member
            timer = self.timers.get(base_tag)
            if timer is not None:
                if member == "pre":
                    timer.pre = int(value)
                    if timer.acc > timer.pre:
                        timer.acc = timer.pre
                    timer.dn = timer.acc >= timer.pre
                    timer.tt = timer.en and not timer.dn
                elif member == "acc":
                    timer.acc = max(0, min(int(value), timer.pre))
                    timer.dn = timer.acc >= timer.pre
                    timer.tt = timer.en and not timer.dn
                elif member == "dn":
                    timer.dn = bool(value)
                elif member == "en":
                    timer.en = bool(value)
                elif member == "tt":
                    timer.tt = bool(value)
                self._sync_timer_tag(base_tag)
                return
            counter = self.counters.get(base_tag)
            if counter is not None:
                if member == "pre":
                    counter.pre = int(value)
                elif member == "acc":
                    counter.acc = int(value)
                elif member == "dn":
                    counter.dn = bool(value)
                counter.dn = counter.acc == counter.pre
                self._sync_counter_tag(base_tag)
                return
        self.set_tag(tag, value)

    def _execute_step(self, step: Step, power_in: bool, scan_ms: int, step_key: str) -> tuple[bool, StepTrace]:
        if step.op == "XIC":
            truth = _coerce_truth(self.read_tag(step.tag))
            power_out = power_in and truth
            return power_out, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_out)
        if step.op == "XIO":
            truth = not _coerce_truth(self.read_tag(step.tag))
            power_out = power_in and truth
            return power_out, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_out)
        operator = step_compare_operator(step)
        if operator is not None:
            left = self.resolve_operand(step.params["left"])
            right = self.resolve_operand(step.params["right"])
            truth = _apply_compare(left, right, operator)
            power_out = power_in and truth
            return power_out, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_out)
        if step.op == "OTE":
            self.write_tag(step.tag, power_in)
            truth = _coerce_truth(self.read_tag(step.tag))
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in)
        if step.op == "OTL":
            if power_in:
                self.write_tag(step.tag, True)
            truth = _coerce_truth(self.read_tag(step.tag))
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in)
        if step.op == "OTU":
            if power_in:
                self.write_tag(step.tag, False)
            truth = _coerce_truth(self.read_tag(step.tag))
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, truth, power_in)
        if step.op == "CTU":
            counter = self.counters.setdefault(step.tag, CounterState())
            if step.arg is not None:
                counter.pre = max(0, int(step.arg))
            previous = self.edge_memory.get(step_key, False)
            if power_in and not previous:
                counter.acc = min(counter.pre, counter.acc + 1)
            counter.dn = counter.acc == counter.pre
            self.edge_memory[step_key] = power_in
            self._sync_counter_tag(step.tag)
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)
        if step.op == "CTD":
            counter = self.counters.setdefault(step.tag, CounterState())
            if step.arg is not None:
                counter.pre = max(0, int(step.arg))
            previous = self.edge_memory.get(step_key, False)
            if power_in and not previous:
                counter.acc = max(0, counter.acc - 1)
            counter.dn = counter.acc == counter.pre
            self.edge_memory[step_key] = power_in
            self._sync_counter_tag(step.tag)
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)
        if step.op == "MOV":
            if power_in:
                self.write_tag(step.tag, self.resolve_operand(step.params["source"]))
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)
        if step.op == "CLR":
            if power_in:
                if step.tag in self.timers:
                    timer = self.timers[step.tag]
                    timer.acc = 0
                    timer.en = False
                    timer.dn = False
                    timer.tt = False
                    self._sync_timer_tag(step.tag)
                elif step.tag in self.counters:
                    counter = self.counters[step.tag]
                    counter.acc = 0
                    counter.dn = False
                    self._sync_counter_tag(step.tag)
                else:
                    self.write_tag(step.tag, 0)
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)
        if step.op == "ABS":
            if power_in:
                self.write_tag(step.tag, abs(self.resolve_operand(step.params["source"])))
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)
        if step.op == "NEG":
            if power_in:
                self.write_tag(step.tag, -self.resolve_operand(step.params["source"]))
            return power_in, StepTrace(step.op, step.tag, step.arg, power_in, power_in, power_in)
        if step.op in {"ADD", "SUB", "MUL", "DIV"}:
            if power_in:
                left = self.resolve_operand(step.params["left"])
                right = self.resolve_operand(step.params["right"])
                self.write_tag(step.tag, _binary_numeric_result(left, right, step.op))
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

    def _execute_nodes(
        self,
        nodes: list[Node],
        power_in: bool,
        scan_ms: int,
        path_prefix: tuple[int, ...] = (),
    ) -> tuple[bool, list[NodeTrace]]:
        current = power_in
        traces: list[NodeTrace] = []
        for node in nodes:
            current_in = current
            if isinstance(node, Step):
                node_index = len(traces)
                node_path = path_prefix + (node_index,)
                current, trace = self._execute_step(node, current, scan_ms, ".".join(str(part) for part in node_path))
            else:
                lane_traces: list[list[NodeTrace]] = []
                lane_outputs: list[bool] = []
                node_index = len(traces)
                for lane_index, lane in enumerate(node.lanes):
                    lane_out, nested = self._execute_nodes(lane, current_in, scan_ms, path_prefix + (node_index, lane_index))
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
        self._sync_all_counter_tags()

        return ScanResult(
            scan_ms=scan_ms,
            rung_power=rung_power,
            tags=dict(sorted(self.tags.items())),
            timers={name: timer.snapshot() for name, timer in sorted(self.timers.items())},
            counters={name: counter.snapshot() for name, counter in sorted(self.counters.items())},
            traces=traces,
        )

    def snapshot(self) -> dict[str, Any]:
        self._sync_all_timer_tags()
        self._sync_all_counter_tags()
        rung_power, traces = trace_program_state(self.program, self.tags, self.forced)
        return {
            "program": self.program.to_dict(),
            "tags": dict(sorted(self.tags.items())),
            "forced": dict(sorted(self.forced.items())),
            "timers": {name: timer.snapshot() for name, timer in sorted(self.timers.items())},
            "counters": {name: counter.snapshot() for name, counter in sorted(self.counters.items())},
            "rung_power": rung_power,
            "traces": traces,
        }
