from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from .engine import BranchTrace, NodeTrace, StepTrace
from .model import Branch, Node, Program, Rung, Step, format_operand, step_compare_operator, step_is_contact, step_primary_tag


ROLE_TEXT = "text"
ROLE_MUTED = "muted"
ROLE_COMMENT = "comment"
ROLE_NUMBER = "number"
ROLE_FLOW_ON = "flow_on"
ROLE_FLOW_OFF = "flow_off"
ROLE_ELEMENT_ON = "element_on"
ROLE_ELEMENT_OFF = "element_off"


def step_token(
    step: Step,
    timer_values: dict[str, dict[str, int | bool]] | None = None,
    counter_values: dict[str, dict[str, int | bool]] | None = None,
    forced_tags: set[str] | None = None,
    show_timer_acc: bool = False,
) -> str:
    forced = (step_primary_tag(step) or "") in (forced_tags or set())
    if step.op == "XIC":
        return f"[f {step.tag}]" if forced else f"[ {step.tag} ]"
    if step.op == "XIO":
        return f"[/f {step.tag}]" if forced else f"[/ {step.tag} ]"
    if step.op == "OTE":
        return f"(f {step.tag})" if forced else f"( {step.tag} )"
    if step.op == "OTL":
        return f"(L f {step.tag})" if forced else f"(L {step.tag})"
    if step.op == "OTU":
        return f"(U f {step.tag})" if forced else f"(U {step.tag})"
    if step.op == "TON":
        timer = (timer_values or {}).get(step.tag)
        if show_timer_acc and timer is not None and "acc" in timer:
            preset = int(timer.get("pre", step.arg or 0))
            width = max(1, len(str(preset)))
            acc = int(timer["acc"])
            prefix = "TON f" if forced else "TON"
            return f"[{prefix} {step.tag} acc:{acc:0{width}d}ms]"
        prefix = "TON f" if forced else "TON"
        preset = int((timer or {}).get("pre", step.arg or 0))
        return f"[{prefix} {step.tag} pre:{preset}ms]"
    if step.op == "CTU":
        counter = (counter_values or {}).get(step.tag, {})
        pre = int(counter.get("pre", step.arg or 0))
        acc = int(counter.get("acc", 0))
        return f"[CTU {'f ' if forced else ''}{step.tag} pre:{pre} acc:{acc}]"
    if step.op == "CTD":
        counter = (counter_values or {}).get(step.tag, {})
        pre = int(counter.get("pre", step.arg or 0))
        acc = int(counter.get("acc", 0))
        return f"[CTD {'f ' if forced else ''}{step.tag} pre:{pre} acc:{acc}]"
    if step.op == "CMP":
        operator = step_compare_operator(step) or "=="
        left = format_operand(step.params["left"])
        right = format_operand(step.params["right"])
        prefix = "CMP f" if forced and isinstance(step.params.get("left"), str) else "CMP"
        return f"[{prefix} {left} {operator} {right}]"
    if step.op in {"EQ", "NE", "GT", "GTE", "LT", "LE"}:
        left = format_operand(step.params["left"])
        right = format_operand(step.params["right"])
        prefix = f"{step.op} f" if forced and isinstance(step.params.get("left"), str) else step.op
        return f"[{prefix} {left} {right}]"
    if step.op == "MOV":
        prefix = "MOV"
        return f"[{prefix} {format_operand(step.params['source'])} -> {'f ' if forced else ''}{step.tag}]"
    if step.op == "CLR":
        return f"[CLR {'f ' if forced else ''}{step.tag}]"
    if step.op in {"ABS", "NEG"}:
        return f"[{step.op} {format_operand(step.params['source'])} -> {'f ' if forced else ''}{step.tag}]"
    if step.op in {"ADD", "SUB", "MUL", "DIV"}:
        return (
            f"[{step.op} {format_operand(step.params['left'])} {format_operand(step.params['right'])} "
            f"-> {'f ' if forced else ''}{step.tag}]"
        )
    raise ValueError(f"Unsupported instruction {step.op}")


def step_segments(
    step: Step,
    role: str,
    timer_values: dict[str, dict[str, int | bool]] | None = None,
    counter_values: dict[str, dict[str, int | bool]] | None = None,
    forced_tags: set[str] | None = None,
    show_timer_acc: bool = False,
) -> list[tuple[str, str]]:
    forced = (step_primary_tag(step) or "") in (forced_tags or set())
    if not forced:
        return [(step_token(step, timer_values, counter_values, forced_tags, show_timer_acc), role)]
    if step.op == "XIC":
        return [("[", role), ("f", ROLE_NUMBER), (f" {step.tag}]", role)]
    if step.op == "XIO":
        return [("[/", role), ("f", ROLE_NUMBER), (f" {step.tag}]", role)]
    if step.op == "OTE":
        return [("(", role), ("f", ROLE_NUMBER), (f" {step.tag})", role)]
    if step.op == "OTL":
        return [("(L ", role), ("f", ROLE_NUMBER), (f" {step.tag})", role)]
    if step.op == "OTU":
        return [("(U ", role), ("f", ROLE_NUMBER), (f" {step.tag})", role)]
    if step.op == "TON":
        timer = (timer_values or {}).get(step.tag)
        if show_timer_acc and timer is not None and "acc" in timer:
            preset = int(timer.get("pre", step.arg or 0))
            width = max(1, len(str(preset)))
            acc = int(timer["acc"])
            suffix = f" {step.tag} acc:{acc:0{width}d}ms]"
        else:
            suffix = f" {step.tag} pre:{int((timer or {}).get('pre', step.arg or 0))}ms]"
        return [("[TON ", role), ("f", ROLE_NUMBER), (suffix, role)]
    if step.op == "CTU":
        counter = (counter_values or {}).get(step.tag, {})
        return [("[CTU ", role), ("f", ROLE_NUMBER), (f" {step.tag} pre:{int(counter.get('pre', step.arg or 0))} acc:{int(counter.get('acc', 0))}]", role)]
    if step.op == "CTD":
        counter = (counter_values or {}).get(step.tag, {})
        return [("[CTD ", role), ("f", ROLE_NUMBER), (f" {step.tag} pre:{int(counter.get('pre', step.arg or 0))} acc:{int(counter.get('acc', 0))}]", role)]
    if step.op == "CMP" and isinstance(step.params.get("left"), str):
        operator = step_compare_operator(step) or "=="
        return [
            ("[CMP ", role),
            ("f", ROLE_NUMBER),
            (f" {format_operand(step.params['left'])} {operator} {format_operand(step.params['right'])}]", role),
        ]
    if step.op in {"EQ", "NE", "GT", "GTE", "LT", "LE"} and isinstance(step.params.get("left"), str):
        return [
            (f"[{step.op} ", role),
            ("f", ROLE_NUMBER),
            (f" {format_operand(step.params['left'])} {format_operand(step.params['right'])}]", role),
        ]
    if step.op == "MOV":
        return [
            (f"[MOV {format_operand(step.params['source'])} -> ", role),
            ("f", ROLE_NUMBER),
            (f" {step.tag}]", role),
        ]
    if step.op == "CLR":
        return [("[CLR ", role), ("f", ROLE_NUMBER), (f" {step.tag}]", role)]
    if step.op in {"ABS", "NEG"}:
        return [
            (f"[{step.op} {format_operand(step.params['source'])} -> ", role),
            ("f", ROLE_NUMBER),
            (f" {step.tag}]", role),
        ]
    if step.op in {"ADD", "SUB", "MUL", "DIV"}:
        return [
            (f"[{step.op} {format_operand(step.params['left'])} {format_operand(step.params['right'])} -> ", role),
            ("f", ROLE_NUMBER),
            (f" {step.tag}]", role),
        ]
    return [(step_token(step, timer_values, counter_values, forced_tags, show_timer_acc), role)]


def node_contains_action(node: Node) -> bool:
    if isinstance(node, Step):
        return not step_is_contact(node)
    return any(node_contains_action(child) for lane in node.lanes for child in lane)


def split_condition_action(
    nodes: list[Node],
    traces: list[NodeTrace],
) -> tuple[int, list[Node], list[NodeTrace], int, list[Node], list[NodeTrace]]:
    split_index = len(nodes)
    for index, node in enumerate(nodes):
        if node_contains_action(node):
            split_index = index
            break
    return 0, nodes[:split_index], traces[:split_index], split_index, nodes[split_index:], traces[split_index:]


def _measure_node(node: Node) -> tuple[int, int]:
    if isinstance(node, Step):
        return len(step_token(node)), 1
    lane_sizes = [_measure_sequence(lane) for lane in node.lanes]
    max_width = max((width for width, _ in lane_sizes), default=4)
    height = sum((height for _, height in lane_sizes), 0) or 1
    return max_width + 2, height


def _measure_sequence(nodes: list[Node]) -> tuple[int, int]:
    if not nodes:
        return 4, 1
    width = 2
    height = 1
    for node in nodes:
        node_width, node_height = _measure_node(node)
        width += node_width + 2
        height = max(height, node_height)
    return width, height


@dataclass(slots=True)
class Cell:
    char: str = " "
    role: str = ROLE_TEXT
    selection_key: str | None = None


@dataclass(slots=True)
class SelectionTarget:
    key: str
    kind: str
    rung_index: int
    path: tuple[int, ...] | None = None


@dataclass(slots=True)
class Span:
    tag: str
    line: int
    start: int
    end: int


@dataclass(slots=True)
class RenderedDocument:
    lines: list[str]
    role_spans: list[Span]
    selection_spans: list[Span]
    selections: dict[str, SelectionTarget]


class GridWriter:
    def __init__(self) -> None:
        self.cells: dict[tuple[int, int], Cell] = {}
        self.width = 0
        self.height = 0

    def set_char(self, x: int, y: int, char: str, role: str, selection_key: str | None = None) -> None:
        if x < 0 or y < 0:
            return
        self.cells[(x, y)] = Cell(char=char, role=role, selection_key=selection_key)
        self.width = max(self.width, x + 1)
        self.height = max(self.height, y + 1)

    def write_text(self, x: int, y: int, text: str, role: str, selection_key: str | None = None) -> None:
        for offset, char in enumerate(text):
            self.set_char(x + offset, y, char, role, selection_key)

    def draw_hline(self, x: int, y: int, length: int, role: str, selection_key: str | None = None) -> None:
        for offset in range(length):
            self.set_char(x + offset, y, "-", role, selection_key)

    def draw_vline(self, x: int, y: int, length: int, role: str, selection_key: str | None = None) -> None:
        for offset in range(length):
            self.set_char(x, y + offset, "|", role, selection_key)

    def to_document(self, selections: dict[str, SelectionTarget]) -> RenderedDocument:
        lines: list[str] = []
        role_spans: list[Span] = []
        selection_spans: list[Span] = []

        for y in range(self.height):
            line_chars: list[str] = []
            roles: list[str] = []
            sels: list[str | None] = []
            for x in range(self.width):
                cell = self.cells.get((x, y), Cell())
                line_chars.append(cell.char)
                roles.append(cell.role)
                sels.append(cell.selection_key)
            lines.append("".join(line_chars).rstrip())

            if not lines[-1]:
                continue

            start = 0
            current_role = roles[0]
            current_sel = sels[0]
            for x in range(1, len(line_chars) + 1):
                next_role = roles[x] if x < len(line_chars) else None
                next_sel = sels[x] if x < len(line_chars) else None
                if next_role != current_role:
                    if any(char != " " for char in line_chars[start:x]):
                        role_spans.append(Span(tag=current_role, line=y, start=start, end=x))
                    start = x
                    current_role = next_role

            start = 0
            current_sel = sels[0]
            for x in range(1, len(line_chars) + 1):
                next_sel = sels[x] if x < len(line_chars) else None
                if next_sel != current_sel:
                    if current_sel and any(char != " " for char in line_chars[start:x]):
                        selection_spans.append(Span(tag=current_sel, line=y, start=start, end=x))
                    start = x
                    current_sel = next_sel

        return RenderedDocument(
            lines=lines,
            role_spans=role_spans,
            selection_spans=selection_spans,
            selections=selections,
        )


class LadderRenderer:
    def __init__(
        self,
        program: Program,
        traces: list[list[NodeTrace]] | None = None,
        timer_values: dict[str, dict[str, int | bool]] | None = None,
        counter_values: dict[str, dict[str, int | bool]] | None = None,
        forced_tags: set[str] | None = None,
        show_timer_acc: bool = False,
    ) -> None:
        self.program = program
        self.traces = traces or [[] for _ in program.rungs]
        self.timer_values = timer_values or {}
        self.counter_values = counter_values or {}
        self.forced_tags = forced_tags or set()
        self.show_timer_acc = show_timer_acc
        self.writer = GridWriter()
        self.selections: dict[str, SelectionTarget] = {}
        self.inner_width = self._compute_inner_width()

    def _compute_inner_width(self) -> int:
        longest = 10
        for rung_index, rung in enumerate(self.program.rungs):
            rung_traces = self.traces[rung_index] if rung_index < len(self.traces) else []
            _, conditions, condition_traces, _, actions, action_traces = split_condition_action(rung.elements, rung_traces)
            condition_width, _ = _measure_sequence_with_timers(conditions, self.timer_values, self.counter_values, self.forced_tags)
            action_width, _ = _measure_sequence_with_timers(actions, self.timer_values, self.counter_values, self.forced_tags)
            longest = max(longest, condition_width + action_width + 4)
        return longest

    def _selection_key(self, kind: str, rung_index: int, path: tuple[int, ...] | None = None) -> str:
        key = f"{kind}:{rung_index}"
        if path:
            key += ":" + ".".join(str(part) for part in path)
        self.selections.setdefault(key, SelectionTarget(key=key, kind=kind, rung_index=rung_index, path=path))
        return key

    def _render_step(
        self,
        step: Step,
        trace: StepTrace | None,
        rung_index: int,
        path: tuple[int, ...],
        x: int,
        y: int,
    ) -> tuple[int, bool]:
        truth = trace.truth if trace else False
        power_out = trace.power_out if trace else False
        role = ROLE_ELEMENT_ON if truth else ROLE_ELEMENT_OFF
        segments = step_segments(step, role, self.timer_values, self.counter_values, self.forced_tags, self.show_timer_acc)
        token = "".join(text for text, _ in segments)
        selection_key = self._selection_key("step", rung_index, path)
        cursor = x
        for text, text_role in segments:
            self.writer.write_text(cursor, y, text, text_role, selection_key)
            cursor += len(text)
        return len(token), power_out

    def _render_branch(
        self,
        branch: Branch,
        trace: BranchTrace | None,
        rung_index: int,
        path: tuple[int, ...],
        x: int,
        y: int,
        rung_key: str,
    ) -> tuple[int, int, bool]:
        lane_sizes = [_measure_sequence_with_timers(lane, self.timer_values, self.counter_values, self.forced_tags) for lane in branch.lanes]
        max_lane_width = max((width for width, _ in lane_sizes), default=4)
        total_width = max_lane_width + 2
        offset_y = 0
        power_in = trace.power_in if trace else False
        lane_outputs = trace.lane_outputs if trace else [False for _ in branch.lanes]
        top_start_key = self._selection_key("branch_start", rung_index, path)
        top_end_key = self._selection_key("branch_end", rung_index, path)

        for lane_index, lane in enumerate(branch.lanes):
            lane_trace = trace.lanes[lane_index] if trace and lane_index < len(trace.lanes) else []
            lane_width, lane_height = lane_sizes[lane_index]
            start_role = ROLE_FLOW_ON if power_in else ROLE_FLOW_OFF
            end_role = ROLE_FLOW_ON if lane_outputs[lane_index] else ROLE_FLOW_OFF

            self.writer.set_char(
                x,
                y + offset_y,
                "+",
                start_role,
                top_start_key if lane_index == 0 else None,
            )
            self.writer.set_char(
                x + total_width - 1,
                y + offset_y,
                "+",
                end_role,
                top_end_key if lane_index == 0 else None,
            )
            if lane_height > 1:
                self.writer.draw_vline(x, y + offset_y + 1, lane_height - 1, start_role, rung_key)
                self.writer.draw_vline(x + total_width - 1, y + offset_y + 1, lane_height - 1, end_role, rung_key)

            _, lane_out = self._render_sequence(
                lane,
                lane_trace,
                rung_index,
                path + (lane_index,),
                x + 1,
                y + offset_y,
                power_in,
                rung_key,
            )
            if lane_width < max_lane_width:
                self.writer.draw_hline(
                    x + 1 + lane_width,
                    y + offset_y,
                    max_lane_width - lane_width,
                    ROLE_FLOW_ON if lane_out else ROLE_FLOW_OFF,
                    rung_key,
                )
            offset_y += lane_height

        return total_width, offset_y, trace.power_out if trace else False

    def _render_sequence(
        self,
        nodes: list[Node],
        traces: list[NodeTrace],
        rung_index: int,
        path_prefix: tuple[int, ...],
        x: int,
        y: int,
        power_in: bool,
        rung_key: str,
        index_offset: int = 0,
    ) -> tuple[int, bool]:
        cursor = x
        current_power = power_in

        if not nodes:
            self.writer.draw_hline(cursor, y, 4, ROLE_FLOW_ON if power_in else ROLE_FLOW_OFF, rung_key)
            return 4, power_in

        for node_index, node in enumerate(nodes):
            self.writer.draw_hline(cursor, y, 2, ROLE_FLOW_ON if current_power else ROLE_FLOW_OFF, rung_key)
            cursor += 2
            trace = traces[node_index] if node_index < len(traces) else None
            node_path = path_prefix + (node_index + index_offset,)
            if isinstance(node, Step):
                node_width, current_power = self._render_step(node, trace if isinstance(trace, StepTrace) else None, rung_index, node_path, cursor, y)
                cursor += node_width
            else:
                node_width, _, current_power = self._render_branch(
                    node,
                    trace if isinstance(trace, BranchTrace) else None,
                    rung_index,
                    node_path,
                    cursor,
                    y,
                    rung_key,
                )
                cursor += node_width

        self.writer.draw_hline(cursor, y, 2, ROLE_FLOW_ON if current_power else ROLE_FLOW_OFF, rung_key)
        cursor += 2
        return cursor - x, current_power

    def _render_rung(self, rung: Rung, rung_index: int, traces: list[NodeTrace], start_y: int) -> int:
        line_y = start_y
        if rung.comment:
            comment_key = self._selection_key("rung", rung_index)
            self.writer.write_text(6, line_y, rung.comment, ROLE_COMMENT, comment_key)
            line_y += 1

        number_key = self._selection_key("rung", rung_index)
        number = f"{rung_index + 1:03d}"
        self.writer.write_text(0, line_y, number, ROLE_NUMBER, number_key)
        self.writer.write_text(3, line_y, " ", ROLE_TEXT)
        self.writer.set_char(4, line_y, "|", ROLE_FLOW_ON, number_key)
        self.writer.write_text(5, line_y, " ", ROLE_TEXT)

        condition_offset, conditions, condition_traces, action_offset, actions, action_traces = split_condition_action(rung.elements, traces)
        condition_width, condition_height = _measure_sequence_with_timers(conditions, self.timer_values, self.counter_values, self.forced_tags)
        action_width, action_height = _measure_sequence_with_timers(actions, self.timer_values, self.counter_values, self.forced_tags)
        seq_height = max(condition_height, action_height, 1)

        _, condition_power = self._render_sequence(
            conditions,
            condition_traces,
            rung_index,
            (),
            6,
            line_y,
            True,
            number_key,
            index_offset=condition_offset,
        )
        filler = max(0, self.inner_width - condition_width - action_width)
        self.writer.draw_hline(6 + condition_width, line_y, filler, ROLE_FLOW_ON if condition_power else ROLE_FLOW_OFF, number_key)
        action_start = 6 + condition_width + filler
        _, final_power = self._render_sequence(
            actions,
            action_traces,
            rung_index,
            (),
            action_start,
            line_y,
            condition_power,
            number_key,
            index_offset=action_offset,
        )
        self.writer.write_text(6 + self.inner_width, line_y, " ", ROLE_TEXT)
        self.writer.set_char(7 + self.inner_width, line_y, "|", ROLE_FLOW_ON if final_power else ROLE_FLOW_OFF, number_key)
        return start_y + seq_height + (1 if rung.comment else 0)

    def render(self) -> RenderedDocument:
        cursor_y = 0
        for rung_index, rung in enumerate(self.program.rungs):
            rung_traces = self.traces[rung_index] if rung_index < len(self.traces) else []
            cursor_y = self._render_rung(rung, rung_index, rung_traces, cursor_y)
            cursor_y += 1
        if not self.program.rungs:
            self.writer.write_text(0, 0, "(no rungs)", ROLE_MUTED)
        return self.writer.to_document(self.selections)


def _measure_node_with_timers(
    node: Node,
    timer_values: dict[str, dict[str, int | bool]],
    counter_values: dict[str, dict[str, int | bool]],
    forced_tags: set[str],
) -> tuple[int, int]:
    if isinstance(node, Step):
        return len(step_token(node, timer_values, counter_values, forced_tags, False)), 1
    lane_sizes = [_measure_sequence_with_timers(lane, timer_values, counter_values, forced_tags) for lane in node.lanes]
    max_width = max((width for width, _ in lane_sizes), default=4)
    height = sum((height for _, height in lane_sizes), 0) or 1
    return max_width + 2, height


def _measure_sequence_with_timers(
    nodes: list[Node],
    timer_values: dict[str, dict[str, int | bool]],
    counter_values: dict[str, dict[str, int | bool]],
    forced_tags: set[str],
) -> tuple[int, int]:
    if not nodes:
        return 4, 1
    width = 2
    height = 1
    for node in nodes:
        node_width, node_height = _measure_node_with_timers(node, timer_values, counter_values, forced_tags)
        width += node_width + 2
        height = max(height, node_height)
    return width, height


def render_program(
    program: Program,
    traces: list[list[NodeTrace]] | None = None,
    timer_values: dict[str, dict[str, int | bool]] | None = None,
    counter_values: dict[str, dict[str, int | bool]] | None = None,
    forced_tags: set[str] | None = None,
) -> str:
    document = LadderRenderer(
        program,
        traces=traces,
        timer_values=timer_values,
        counter_values=counter_values,
        forced_tags=forced_tags,
        show_timer_acc=timer_values is not None,
    ).render()
    return "\n".join(document.lines)
