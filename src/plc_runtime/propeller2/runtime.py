from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from plc_ascii.model import Binding, Branch, Node, Program, Step, Variable, split_timer_member, step_compare_operator
from plc_runtime.base import BoardRuntime

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover
    serial = None


DEFAULT_SCAN_MS = 50
PROGRAM_HEX_CHUNK_SIZE = 96
DEFAULT_ACTIVE_LOW_OUTPUTS = {56, 57, 58, 59, 60, 61, 62, 63}
SUPPORTED_VARIABLE_TYPES = {"bool", "int", "timer", "counter"}
DATA_RAM_BASE = 0x12000


class Propeller2RuntimeError(RuntimeError):
    """Raised when the TAQOZ runtime cannot be built or loaded."""


@dataclass(slots=True)
class ScalarBinding:
    binding: Binding
    address: int


@dataclass(slots=True)
class TimerSymbols:
    word: str
    pre: str
    acc: str
    dn: str
    en: str
    tt: str


@dataclass(slots=True)
class CounterSymbols:
    up_word: str
    down_word: str
    up_edge: str
    down_edge: str
    pre: str
    acc: str
    dn: str


@dataclass(slots=True)
class CompileContext:
    program: Program
    scan_ms: int
    scalar_variables: list[Variable]
    timer_variables: list[Variable]
    counter_variables: list[Variable]
    mode_symbol: str = ""
    scan_ms_symbol: str = ""
    scalar_symbols: dict[str, str] = field(default_factory=dict)
    timer_symbols: dict[str, TimerSymbols] = field(default_factory=dict)
    counter_symbols: dict[str, CounterSymbols] = field(default_factory=dict)
    input_bindings: list[ScalarBinding] = field(default_factory=list)
    output_bindings: list[ScalarBinding] = field(default_factory=list)
    branch_symbols: list[tuple[str, str]] = field(default_factory=list)
    _branch_index: int = 0
    _next_address: int = DATA_RAM_BASE

    def alloc_branch_symbols(self) -> tuple[str, str]:
        self._branch_index += 1
        symbols = (self.alloc_long_symbol(), self.alloc_long_symbol())
        self.branch_symbols.append(symbols)
        return symbols

    def alloc_long_symbol(self) -> str:
        address = self._next_address
        self._next_address += 4
        return f"${address:05X}"


class TaqozConsole:
    PROMPT = "TAQOZ# "

    def __init__(self, serial_port: Any) -> None:
        self.serial_port = serial_port

    def enter_taqoz(self, *, reset: bool = True, timeout: float = 2.0) -> str:
        self.serial_port.reset_input_buffer()
        if reset:
            self.serial_port.write(bytes([0x3E, 0x20, 0x1B]))
            time.sleep(0.6)
        else:
            self.serial_port.write(b"\r")
            time.sleep(0.05)
        return self.read_until_prompt(timeout=timeout)

    def read_until_prompt(self, timeout: float = 2.0) -> str:
        deadline = time.monotonic() + timeout
        chunks: list[bytes] = []
        while time.monotonic() < deadline:
            chunk = self.serial_port.read(512)
            if chunk:
                chunks.append(chunk)
                text = b"".join(chunks).decode("utf-8", "ignore")
                if self.PROMPT in text:
                    return text
                continue
            time.sleep(0.01)
        return b"".join(chunks).decode("utf-8", "ignore")

    def send_command(self, command: str, timeout: float = 2.0) -> str:
        self.serial_port.write(command.encode("utf-8") + b"\r")
        time.sleep(0.05)
        return self.read_until_prompt(timeout=timeout)

    def send_source(self, source: str, timeout: float = 2.0) -> list[str]:
        responses: list[str] = []
        pending_definition: list[str] = []
        commands: list[str] = []
        for raw_line in source.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if pending_definition:
                pending_definition.append(line)
                if line == ";":
                    commands.append(" ".join(pending_definition))
                    pending_definition = []
                continue
            if line.startswith(":") and line != ";":
                pending_definition = [line]
                if line.endswith(" ;"):
                    commands.append(" ".join(pending_definition))
                    pending_definition = []
                continue
            commands.append(line)
        if pending_definition:
            commands.append(" ".join(pending_definition))

        for line in commands:
            response = self.send_command(line, timeout=timeout)
            if "???" in response:
                raise Propeller2RuntimeError(f"TAQOZ rejected line '{line}': {response.strip()}")
            responses.append(response)
        return responses


def open_serial_port(port: str, baudrate: int = 115200, timeout: float = 0.2) -> Any:
    if serial is None:
        raise Propeller2RuntimeError("pyserial is not installed. Install with: pip install -e .[serial]")
    serial_port = serial.Serial()
    serial_port.port = port
    serial_port.baudrate = baudrate
    serial_port.timeout = timeout
    serial_port.dtr = False
    serial_port.rts = False
    serial_port.open()
    return serial_port


def _bool_word(value: bool) -> str:
    return "1" if value else "0"


def _binding_address(binding: Binding) -> int:
    try:
        address = int(str(binding.address).strip(), 10)
    except ValueError as exc:
        raise Propeller2RuntimeError(
            f"Propeller 2 bindings must use numeric pin addresses, got '{binding.address}'"
        ) from exc
    if address < 0 or address > 63:
        raise Propeller2RuntimeError(f"Propeller 2 pin address {address} is out of range 0..63")
    return address


def _normalize_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not value.is_integer():
            raise Propeller2RuntimeError("REAL values are not supported by the Propeller 2 TAQOZ runtime yet")
        return str(int(value))
    raise Propeller2RuntimeError(f"Unsupported literal value: {value!r}")


def _build_context(program: Program, scan_ms: int) -> CompileContext:
    program.validate()
    scalar_variables = [variable for variable in program.variables if variable.data_type in {"bool", "int"}]
    timer_variables = [variable for variable in program.variables if variable.data_type == "timer"]
    counter_variables = [variable for variable in program.variables if variable.data_type == "counter"]
    for variable in program.variables:
        if variable.data_type not in SUPPORTED_VARIABLE_TYPES:
            raise Propeller2RuntimeError(
                f"Variable '{variable.tag}' uses type '{variable.data_type}'. "
                "The Propeller 2 TAQOZ runtime currently supports BOOL, DINT, TIMER, and COUNTER."
            )

    context = CompileContext(
        program=program,
        scan_ms=max(1, int(scan_ms)),
        scalar_variables=scalar_variables,
        timer_variables=timer_variables,
        counter_variables=counter_variables,
    )
    context.mode_symbol = context.alloc_long_symbol()
    context.scan_ms_symbol = context.alloc_long_symbol()

    for index, variable in enumerate(scalar_variables):
        _ = index
        context.scalar_symbols[variable.tag] = context.alloc_long_symbol()

    timer_configs = list(program.timer_configs().values())
    for index, timer in enumerate(timer_configs):
        context.timer_symbols[timer.tag] = TimerSymbols(
            word=f"PLC.TON.{index}",
            pre=context.alloc_long_symbol(),
            acc=context.alloc_long_symbol(),
            dn=context.alloc_long_symbol(),
            en=context.alloc_long_symbol(),
            tt=context.alloc_long_symbol(),
        )

    counter_configs = list(program.counter_configs().values())
    for index, counter in enumerate(counter_configs):
        context.counter_symbols[counter.tag] = CounterSymbols(
            up_word=f"PLC.CTU.{index}",
            down_word=f"PLC.CTD.{index}",
            up_edge=context.alloc_long_symbol(),
            down_edge=context.alloc_long_symbol(),
            pre=context.alloc_long_symbol(),
            acc=context.alloc_long_symbol(),
            dn=context.alloc_long_symbol(),
        )

    for binding in program.bindings:
        address = _binding_address(binding)
        if binding.direction == "input":
            if binding.tag not in context.scalar_symbols:
                raise Propeller2RuntimeError(
                    f"Input binding '{binding.tag}' must target a top-level BOOL or DINT tag on Propeller 2"
                )
            context.input_bindings.append(ScalarBinding(binding=binding, address=address))
            continue
        context.output_bindings.append(ScalarBinding(binding=binding, address=address))

    for rung in program.rungs:
        for step in _walk_steps(rung.elements):
            if step.op == "MOV" and _operand_is_float(step.params.get("source")):
                raise Propeller2RuntimeError("MOV with REAL operands is not supported by the Propeller 2 TAQOZ runtime yet")
            if step.op in {"ADD", "SUB", "MUL", "DIV", "CMP", "EQ", "GT", "GTE", "LT", "LE", "NE"}:
                if _operand_is_float(step.params.get("left")) or _operand_is_float(step.params.get("right")):
                    raise Propeller2RuntimeError(
                        f"{step.op} with REAL operands is not supported by the Propeller 2 TAQOZ runtime yet"
                    )
            if step.op in {"ABS", "NEG"} and _operand_is_float(step.params.get("source")):
                raise Propeller2RuntimeError(f"{step.op} with REAL operands is not supported by the Propeller 2 TAQOZ runtime yet")
    return context


def _walk_steps(nodes: list[Node]) -> list[Step]:
    steps: list[Step] = []
    for node in nodes:
        if isinstance(node, Step):
            steps.append(node)
        else:
            for lane in node.lanes:
                steps.extend(_walk_steps(lane))
    return steps


def _operand_is_float(value: Any) -> bool:
    return isinstance(value, float) and not float(value).is_integer()


def _read_symbol(context: CompileContext, tag: str) -> str:
    if tag in context.scalar_symbols:
        return context.scalar_symbols[tag]
    parts = split_timer_member(tag)
    if parts is not None:
        base, member = parts
        if base in context.timer_symbols:
            timer = context.timer_symbols[base]
            mapping = {
                "pre": timer.pre,
                "acc": timer.acc,
                "dn": timer.dn,
                "en": timer.en,
                "tt": timer.tt,
            }
            if member in mapping:
                return mapping[member]
        if base in context.counter_symbols:
            counter = context.counter_symbols[base]
            mapping = {
                "pre": counter.pre,
                "acc": counter.acc,
                "dn": counter.dn,
            }
            if member in mapping:
                return mapping[member]
    raise Propeller2RuntimeError(f"Tag '{tag}' is not available in the Propeller 2 runtime")


def _emit_operand(context: CompileContext, operand: Any) -> str:
    if isinstance(operand, str):
        return f"{_read_symbol(context, operand)} @"
    return _normalize_literal(operand)


def _emit_bool_store(symbol: str) -> str:
    return f"PLC.BOOL {symbol} !"


def _emit_scalar_store(context: CompileContext, tag: str) -> str:
    if tag not in context.scalar_symbols:
        raise Propeller2RuntimeError(f"Tag '{tag}' cannot be written directly on the Propeller 2 runtime")
    variable_type = next(variable.data_type for variable in context.scalar_variables if variable.tag == tag)
    if variable_type == "bool":
        return _emit_bool_store(context.scalar_symbols[tag])
    return f"{context.scalar_symbols[tag]} !"


def _emit_timer_word(symbols: TimerSymbols, scan_ms_symbol: str) -> list[str]:
    return [
        f": {symbols.word}",
        f"  DUP {symbols.en} !",
        "  DUP IF",
        f"    {symbols.acc} @ {scan_ms_symbol} @ + {symbols.pre} @ MIN {symbols.acc} !",
        f"    {symbols.acc} @ {symbols.pre} @ => PLC.BOOL {symbols.dn} !",
        f"    {symbols.dn} @ 0= PLC.BOOL {symbols.tt} !",
        "  ELSE",
        f"    0 {symbols.acc} !",
        f"    0 {symbols.dn} !",
        f"    0 {symbols.tt} !",
        "  THEN",
        ";",
    ]


def _emit_counter_up_word(symbols: CounterSymbols) -> list[str]:
    return [
        f": {symbols.up_word}",
        "  DUP IF",
        f"    {symbols.up_edge} @ 0= IF",
        f"      {symbols.acc} @ 1+ {symbols.pre} @ MIN {symbols.acc} !",
        "    THEN",
        "  THEN",
        f"  DUP {symbols.up_edge} !",
        f"  {symbols.acc} @ {symbols.pre} @ = PLC.BOOL {symbols.dn} !",
        ";",
    ]


def _emit_counter_down_word(symbols: CounterSymbols) -> list[str]:
    return [
        f": {symbols.down_word}",
        "  DUP IF",
        f"    {symbols.down_edge} @ 0= IF",
        f"      {symbols.acc} @ 1- 0 MAX {symbols.acc} !",
        "    THEN",
        "  THEN",
        f"  DUP {symbols.down_edge} !",
        f"  {symbols.acc} @ {symbols.pre} @ = PLC.BOOL {symbols.dn} !",
        ";",
    ]


def _emit_branch(context: CompileContext, branch: Branch, lines: list[str]) -> None:
    in_symbol, out_symbol = context.alloc_branch_symbols()
    lines.append(f"DUP {in_symbol} ! DROP")
    lines.append(f"{in_symbol} @")
    _emit_nodes(context, branch.lanes[0], lines)
    lines.append(f"{out_symbol} !")
    for lane in branch.lanes[1:]:
        lines.append(f"{out_symbol} @ {in_symbol} @")
        _emit_nodes(context, lane, lines)
        lines.append(f"OR PLC.BOOL {out_symbol} !")
    lines.append(f"{out_symbol} @")


def _emit_step(context: CompileContext, step: Step, lines: list[str]) -> None:
    operator = step_compare_operator(step)
    if step.op == "XIC":
        lines.append(f"{_read_symbol(context, step.tag)} @ AND PLC.BOOL")
        return
    if step.op == "XIO":
        lines.append(f"{_read_symbol(context, step.tag)} @ 0= PLC.BOOL AND")
        return
    if operator is not None:
        operator_word = {
            "==": "=",
            "!=": "<>",
            ">": ">",
            ">=": "=>",
            "<": "<",
            "<=": "<=",
        }[operator]
        lines.append(f"{_emit_operand(context, step.params['left'])} {_emit_operand(context, step.params['right'])} {operator_word} PLC.BOOL AND")
        return
    if step.op == "OTE":
        lines.append(f"DUP {_emit_scalar_store(context, step.tag)}")
        return
    if step.op == "OTL":
        lines.append(f"DUP IF 1 {_emit_scalar_store(context, step.tag)} THEN")
        return
    if step.op == "OTU":
        lines.append(f"DUP IF 0 {_emit_scalar_store(context, step.tag)} THEN")
        return
    if step.op == "TON":
        lines.append(context.timer_symbols[step.tag].word)
        return
    if step.op == "CTU":
        lines.append(context.counter_symbols[step.tag].up_word)
        return
    if step.op == "CTD":
        lines.append(context.counter_symbols[step.tag].down_word)
        return
    if step.op == "MOV":
        lines.append(f"DUP IF {_emit_operand(context, step.params['source'])} {_emit_scalar_store(context, step.tag)} THEN")
        return
    if step.op == "CLR":
        if step.tag in context.timer_symbols:
            timer = context.timer_symbols[step.tag]
            lines.append(
                " ".join(
                    [
                        "DUP IF",
                        f"0 {timer.acc} !",
                        f"0 {timer.en} !",
                        f"0 {timer.dn} !",
                        f"0 {timer.tt} !",
                        "THEN",
                    ]
                )
            )
            return
        if step.tag in context.counter_symbols:
            counter = context.counter_symbols[step.tag]
            lines.append(
                " ".join(
                    [
                        "DUP IF",
                        f"0 {counter.acc} !",
                        f"0 {counter.dn} !",
                        "THEN",
                    ]
                )
            )
            return
        lines.append(f"DUP IF 0 {_emit_scalar_store(context, step.tag)} THEN")
        return
    if step.op == "ABS":
        lines.append(f"DUP IF {_emit_operand(context, step.params['source'])} ABS {_emit_scalar_store(context, step.tag)} THEN")
        return
    if step.op == "NEG":
        lines.append(f"DUP IF {_emit_operand(context, step.params['source'])} NEGATE {_emit_scalar_store(context, step.tag)} THEN")
        return
    if step.op in {"ADD", "SUB", "MUL", "DIV"}:
        operator_word = {"ADD": "+", "SUB": "-", "MUL": "*", "DIV": "/"}[step.op]
        lines.append(
            f"DUP IF {_emit_operand(context, step.params['left'])} {_emit_operand(context, step.params['right'])} {operator_word} {_emit_scalar_store(context, step.tag)} THEN"
        )
        return
    raise Propeller2RuntimeError(f"Instruction '{step.op}' is not supported by the Propeller 2 TAQOZ runtime")


def _emit_nodes(context: CompileContext, nodes: list[Node], lines: list[str]) -> None:
    for node in nodes:
        if isinstance(node, Step):
            _emit_step(context, node, lines)
            continue
        _emit_branch(context, node, lines)


class Propeller2Runtime(BoardRuntime):
    target_name = "Propeller 2"

    def board_files(self, program: Program | None = None, **kwargs: Any) -> dict[str, str]:
        if program is None:
            raise Propeller2RuntimeError("A ladder program is required to build the Propeller 2 runtime")
        scan_ms = int(kwargs.get("scan_ms", DEFAULT_SCAN_MS))
        return {"runtime.fth": self.build_runtime_source(program, scan_ms=scan_ms)}

    def build_runtime_source(self, program: Program, scan_ms: int = DEFAULT_SCAN_MS) -> str:
        context = _build_context(program, scan_ms)
        serialized_program = json.dumps(program.to_dict(), separators=(",", ":"))
        program_hex = serialized_program.encode("utf-8").hex()
        program_chunks = [
            program_hex[index : index + PROGRAM_HEX_CHUNK_SIZE]
            for index in range(0, len(program_hex), PROGRAM_HEX_CHUNK_SIZE)
        ] or [""]

        core_words = [
            ": PLC.BOOL 0<> IF 1 ELSE 0 THEN ;",
            ": PLC.HELLO .\" PLC HELLO 1\" CRLF ;",
            f": PLC.RUN 1 {context.mode_symbol} ! ;",
            f": PLC.STOP 0 {context.mode_symbol} ! ;",
        ]

        timer_words: list[str] = []
        for symbols in context.timer_symbols.values():
            timer_words.extend(_emit_timer_word(symbols, context.scan_ms_symbol))

        counter_words: list[str] = []
        for symbols in context.counter_symbols.values():
            counter_words.extend(_emit_counter_up_word(symbols))
            counter_words.extend(_emit_counter_down_word(symbols))

        rung_words: list[str] = []
        for index, rung in enumerate(program.rungs):
            rung_lines = [f": PLC.RUNG.{index}", "  1"]
            _emit_nodes(context, rung.elements, rung_lines)
            rung_lines.extend(["  DROP", ";"])
            rung_words.extend(rung_lines)

        input_lines: list[str] = []
        for item in context.input_bindings:
            invert = "0= PLC.BOOL" if item.address in DEFAULT_ACTIVE_LOW_OUTPUTS else "0<> PLC.BOOL"
            input_lines.append(f"  {item.address} PIN@ {invert} {_emit_scalar_store(context, item.binding.tag)}")

        output_lines: list[str] = []
        for item in context.output_bindings:
            state = _read_symbol(context, item.binding.tag)
            if item.address in DEFAULT_ACTIVE_LOW_OUTPUTS:
                output_lines.append(f"  {state} @ IF {item.address} LOW ELSE {item.address} HIGH THEN")
            else:
                output_lines.append(f"  {state} @ IF {item.address} HIGH ELSE {item.address} LOW THEN")

        scan_rung_calls = [f"  PLC.RUNG.{index}" for index, _rung in enumerate(program.rungs)]
        set_words = [
            f": PLC.SET.{index} {_emit_scalar_store(context, variable.tag)} ;"
            for index, variable in enumerate(context.scalar_variables)
        ]

        snapshot_lines = [f"  .\" PLC MODE \" {context.mode_symbol} @ . CRLF"]
        for index, variable in enumerate(context.scalar_variables):
            snapshot_lines.append(f"  .\" PLC VAR {index} \" {context.scalar_symbols[variable.tag]} @ . CRLF")
        for index, timer in enumerate(program.timer_configs().values()):
            symbols = context.timer_symbols[timer.tag]
            snapshot_lines.append(
                " ".join(
                    [
                        f"  .\" PLC TIMER {index} \"",
                        f"{symbols.pre} @ .",
                        f"{symbols.acc} @ .",
                        f"{symbols.dn} @ .",
                        f"{symbols.en} @ .",
                        f"{symbols.tt} @ .",
                        "CRLF",
                    ]
                )
            )
        for index, counter in enumerate(program.counter_configs().values()):
            symbols = context.counter_symbols[counter.tag]
            snapshot_lines.append(
                " ".join(
                    [
                        f"  .\" PLC COUNTER {index} \"",
                        f"{symbols.pre} @ .",
                        f"{symbols.acc} @ .",
                        f"{symbols.dn} @ .",
                        "CRLF",
                    ]
                )
            )

        upload_lines = [f"  .\" PLC CHUNK {index} {chunk}\" CRLF" for index, chunk in enumerate(program_chunks)]

        init_lines = [
            f"  {context.scan_ms} {context.scan_ms_symbol} !",
            f"  1 {context.mode_symbol} !",
        ]
        for variable in context.scalar_variables:
            initial = variable.initial if variable.initial is not None else 0
            init_lines.append(f"  {_normalize_literal(initial)} {context.scalar_symbols[variable.tag]} !")
        for timer in program.timer_configs().values():
            symbols = context.timer_symbols[timer.tag]
            init_lines.append(f"  {int(timer.preset_ms)} {symbols.pre} !")
            init_lines.append(f"  0 {symbols.acc} !")
            init_lines.append(f"  0 {symbols.dn} !")
            init_lines.append(f"  0 {symbols.en} !")
            init_lines.append(f"  0 {symbols.tt} !")
        for counter in program.counter_configs().values():
            symbols = context.counter_symbols[counter.tag]
            init_lines.append(f"  0 {symbols.up_edge} !")
            init_lines.append(f"  0 {symbols.down_edge} !")
            init_lines.append(f"  {int(counter.preset)} {symbols.pre} !")
            init_lines.append(f"  0 {symbols.acc} !")
            init_lines.append(f"  0 {symbols.dn} !")

        template = self.resource_text("runtime.fth")
        sections = {
            "@@CORE_WORDS@@": "\n".join(core_words),
            "@@TIMER_WORDS@@": "\n".join(timer_words),
            "@@COUNTER_WORDS@@": "\n".join(counter_words),
            "@@RUNG_WORDS@@": "\n".join(rung_words),
            "@@INPUT_LINES@@": "\n".join(input_lines),
            "@@OUTPUT_LINES@@": "\n".join(output_lines),
            "@@SCAN_RUNG_CALLS@@": "\n".join(scan_rung_calls),
            "@@SET_WORDS@@": "\n".join(set_words),
            "@@SNAPSHOT_LINES@@": "\n".join(snapshot_lines),
            "@@UPLOAD_LINES@@": "\n".join(upload_lines),
            "@@INIT_LINES@@": "\n".join(init_lines),
        }
        for marker, content in sections.items():
            template = template.replace(marker, content)
        return template if template.endswith("\n") else template + "\n"

    def install(
        self,
        port: str,
        *,
        program: Program,
        baudrate: int = 115200,
        scan_ms: int = DEFAULT_SCAN_MS,
    ) -> None:
        serial_port = open_serial_port(port, baudrate=baudrate)
        try:
            console = TaqozConsole(serial_port)
            console.enter_taqoz(reset=True, timeout=2.5)
            console.send_source(self.build_runtime_source(program, scan_ms=scan_ms), timeout=2.0)
        finally:
            serial_port.close()


_RUNTIME = Propeller2Runtime()


def build_runtime_source(program: Program, scan_ms: int = DEFAULT_SCAN_MS) -> str:
    return _RUNTIME.build_runtime_source(program, scan_ms=scan_ms)


def install_runtime(
    port: str,
    *,
    program: Program,
    baudrate: int = 115200,
    scan_ms: int = DEFAULT_SCAN_MS,
) -> None:
    _RUNTIME.install(port, program=program, baudrate=baudrate, scan_ms=scan_ms)
