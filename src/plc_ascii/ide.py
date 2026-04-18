from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font, messagebox, simpledialog, ttk

import markdown
from .circuitpython import install_runtime as install_circuitpython_runtime
from .engine import LadderEngine, ScanResult, trace_program_preview, trace_program_state
from .model import Binding, Branch, Node, Program, Rung, Step, Variable, split_timer_member, step_primary_tag, walk_steps
from .program_io import load_program, save_program
from .remote import RemoteSession
from .render import (
    ROLE_COMMENT,
    ROLE_ELEMENT_OFF,
    ROLE_ELEMENT_ON,
    ROLE_FLOW_OFF,
    ROLE_FLOW_ON,
    ROLE_MUTED,
    ROLE_NUMBER,
    ROLE_TEXT,
    LadderRenderer,
    RenderedDocument,
    SelectionTarget,
)
from .serial_link import SerialJsonTransport
from tkinterweb import HtmlFrame

try:
    from serial.tools import list_ports  # type: ignore
except Exception:  # pragma: no cover
    list_ports = None


PALETTE = {
    "bg": "#1f2329",
    "panel": "#262b31",
    "panel_alt": "#2d333b",
    "border": "#323842",
    "text": "#f2f4f8",
    "muted": "#9aa4b2",
    "accent": "#ff5b4d",
    "accent_alt": "#ffb938",
    "success": "#45c08a",
    "danger": "#ff6b5d",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS_PATH = REPO_ROOT / "DOCS.md"
README_PATH = REPO_ROOT / "README.md"
HELP_PATH = REPO_ROOT / "HELP.md"

MARKDOWN_VIEWER_CSS = """
body {
  background: #1f2329;
  color: #f2f4f8;
  font-family: Helvetica, Arial, sans-serif;
  font-size: __BODY_FONT_PX__px;
  line-height: 1.6;
  margin: 0 auto;
  max-width: 980px;
  padding: 28px 32px 48px;
}
h1, h2, h3, h4 {
  color: #ffb938;
  line-height: 1.2;
}
h1 { border-bottom: 1px solid #323842; padding-bottom: 10px; font-size: __H1_FONT_PX__px; }
h2 { border-bottom: 1px solid #323842; padding-bottom: 8px; margin-top: 32px; font-size: __H2_FONT_PX__px; }
h3 { font-size: __H3_FONT_PX__px; }
h4 { font-size: __H4_FONT_PX__px; }
p, li { color: #f2f4f8; }
a { color: #45c08a; }
code {
  background: #2d333b;
  border-radius: 4px;
  color: #ffb938;
  padding: 2px 5px;
}
pre {
  background: #262b31;
  border: 1px solid #323842;
  border-radius: 10px;
  overflow-x: auto;
  padding: 14px 16px;
}
pre code {
  background: transparent;
  color: #f2f4f8;
  padding: 0;
}
blockquote {
  border-left: 4px solid #ff5b4d;
  color: #c7d0db;
  margin: 18px 0;
  padding-left: 16px;
}
table {
  border-collapse: collapse;
  margin: 16px 0 24px;
  width: 100%;
}
th, td {
  border: 1px solid #323842;
  padding: 10px 12px;
  text-align: left;
}
th {
  background: #262b31;
  color: #ffb938;
}
td {
  background: #2d333b;
}
hr {
  border: none;
  border-top: 1px solid #323842;
  margin: 28px 0;
}
"""


ROLE_TO_COLOR = {
    ROLE_TEXT: PALETTE["text"],
    ROLE_MUTED: PALETTE["muted"],
    ROLE_COMMENT: PALETTE["muted"],
    ROLE_NUMBER: PALETTE["accent_alt"],
    ROLE_FLOW_ON: PALETTE["success"],
    ROLE_FLOW_OFF: PALETTE["muted"],
    ROLE_ELEMENT_ON: PALETTE["success"],
    ROLE_ELEMENT_OFF: PALETTE["danger"],
}

TYPE_DISPLAY_NAMES = {
    "bool": "BOOL",
    "int": "DINT",
    "float": "REAL",
    "timer": "TIMER",
    "counter": "COUNTER",
}

DISPLAY_TO_TYPE_NAMES = {label: data_type for data_type, label in TYPE_DISPLAY_NAMES.items()}


def display_type_name(data_type: str) -> str:
    return TYPE_DISPLAY_NAMES.get(data_type, data_type.upper())


def parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "on", "yes"}:
        return True
    if value in {"0", "false", "off", "no"}:
        return False
    raise ValueError(f"Cannot parse boolean from '{raw}'")


def parse_scalar_or_tag(raw: str) -> str | int | float:
    text = raw.strip()
    if not text:
        raise ValueError("Value cannot be empty")
    try:
        if "." not in text and "e" not in text.lower():
            return int(text)
        return float(text)
    except ValueError:
        return text


def parse_runtime_value(raw: str) -> bool | int | float:
    text = raw.strip()
    lowered = text.lower()
    if lowered in {"true", "on", "yes"}:
        return True
    if lowered in {"false", "off", "no"}:
        return False
    value = parse_scalar_or_tag(text)
    if isinstance(value, str):
        raise ValueError(f"Cannot parse runtime value from '{raw}'")
    return value


def ask_bool(parent: tk.Misc, title: str, prompt: str, initial: str = "0") -> bool | None:
    raw = simpledialog.askstring(title, prompt, parent=parent, initialvalue=initial)
    if raw is None:
        return None
    return parse_bool(raw)


def ask_runtime_value(parent: tk.Misc, title: str, prompt: str, initial: str = "0") -> bool | int | float | None:
    raw = simpledialog.askstring(title, prompt, parent=parent, initialvalue=initial)
    if raw is None:
        return None
    return parse_runtime_value(raw)


def format_runtime_value(value: bool | int | float) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float):
        return format(value, "g")
    return str(value)


def infer_scalar_type(value: bool | int | float) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, float):
        return "float"
    return "int"


def infer_program_variable_types(program: Program) -> tuple[dict[str, str], dict[str, int], dict[str, int]]:
    inferred: dict[str, str] = {}
    timer_presets: dict[str, int] = {}
    counter_presets: dict[str, int] = {}
    variable_map = program.variable_map()

    def known_numeric_type(tag: str) -> str | None:
        variable = variable_map.get(tag)
        if variable is not None and variable.data_type in {"int", "float"}:
            return variable.data_type
        return inferred.get(tag) if inferred.get(tag) in {"int", "float"} else None

    for binding in program.bindings:
        inferred.setdefault(binding.tag, "bool")

    for rung in program.rungs:
        for step in walk_steps(rung.elements):
            if step.op in {"XIC", "XIO", "OTE", "OTL", "OTU"} and "." not in step.tag:
                inferred.setdefault(step.tag, "bool")
                continue
            if step.op == "TON":
                inferred[step.tag] = "timer"
                next_preset = int(step.arg or timer_presets.get(step.tag, 0))
                if step.tag in timer_presets and timer_presets[step.tag] != next_preset:
                    raise ValueError(f"Timer {step.tag} uses conflicting presets")
                timer_presets[step.tag] = next_preset
                continue
            if step.op in {"CTU", "CTD"}:
                inferred[step.tag] = "counter"
                next_preset = int(step.arg or counter_presets.get(step.tag, 0))
                if step.tag in counter_presets and counter_presets[step.tag] != next_preset:
                    raise ValueError(f"Counter {step.tag} uses conflicting presets")
                counter_presets[step.tag] = next_preset
                continue

            float_hint = False
            for key in ("source", "left", "right"):
                operand = step.params.get(key)
                if isinstance(operand, float):
                    float_hint = True
                elif isinstance(operand, str):
                    float_hint = float_hint or known_numeric_type(operand) == "float"
            numeric_type = "float" if float_hint else "int"

            if step.op in {"MOV", "CLR", "ADD", "ABS", "MUL", "DIV", "NEG", "SUB"} and step.tag and "." not in step.tag:
                inferred.setdefault(step.tag, numeric_type)
                for key in ("source", "left", "right"):
                    operand = step.params.get(key)
                    if isinstance(operand, str) and "." not in operand:
                        inferred.setdefault(operand, numeric_type)
                continue

            if step.op in {"CMP", "EQ", "GT", "GTE", "LT", "LE", "NE"}:
                for key in ("left", "right"):
                    operand = step.params.get(key)
                    if isinstance(operand, str) and "." not in operand:
                        inferred.setdefault(operand, numeric_type)

    return inferred, timer_presets, counter_presets


def populate_program_variables(program: Program, current_values: dict[str, object] | None = None) -> None:
    inferred, timer_presets, counter_presets = infer_program_variable_types(program)
    variable_map = program.variable_map()

    for tag, data_type in inferred.items():
        if tag in variable_map:
            variable = variable_map[tag]
            if variable.data_type != data_type:
                raise ValueError(f"Variable {tag} is declared as {variable.data_type} but is used as {data_type}")
            continue
        if data_type == "bool":
            program.variables.append(Variable(tag=tag, data_type=data_type, initial=False))
        elif data_type == "int":
            program.variables.append(Variable(tag=tag, data_type=data_type, initial=0))
        elif data_type == "float":
            program.variables.append(Variable(tag=tag, data_type=data_type, initial=0.0))
        elif data_type == "timer":
            program.variables.append(Variable(tag=tag, data_type=data_type, preset=timer_presets.get(tag, 0)))
        elif data_type == "counter":
            program.variables.append(Variable(tag=tag, data_type=data_type, preset=counter_presets.get(tag, 0)))

    for variable in program.variables:
        if variable.data_type == "timer" and variable.tag in timer_presets:
            variable.preset = timer_presets[variable.tag]
        elif variable.data_type == "counter" and variable.tag in counter_presets:
            variable.preset = counter_presets[variable.tag]

    if current_values is None:
        program.validate()
        return

    for variable in program.variables:
        if variable.data_type == "bool" and variable.tag in current_values:
            variable.initial = bool(current_values[variable.tag])
        elif variable.data_type == "int" and variable.tag in current_values:
            variable.initial = int(current_values[variable.tag])
        elif variable.data_type == "float" and variable.tag in current_values:
            variable.initial = float(current_values[variable.tag])
        elif variable.data_type in {"timer", "counter"}:
            preset_key = f"{variable.tag}.pre"
            if preset_key in current_values:
                variable.preset = int(current_values[preset_key])

    program.validate()


def validate_program_step_types(program: Program, step: Step) -> None:
    variable_map = program.variable_map()

    def ensure_boolean_ref(tag: str, *, allow_members: bool) -> None:
        parts = split_timer_member(tag)
        if parts is None:
            variable = variable_map.get(tag)
            if variable is not None and variable.data_type != "bool":
                raise ValueError(f"{tag} is a {variable.data_type} variable and cannot be used in a boolean instruction")
            return
        base, member = parts
        variable = variable_map.get(base)
        if not allow_members:
            raise ValueError(f"{tag} cannot be used here")
        if variable is None:
            if member not in {"dn", "en", "tt"}:
                raise ValueError(f"{tag} is not a valid boolean member")
            return
        if variable.data_type == "timer" and member in {"en", "dn", "tt"}:
            return
        if variable.data_type == "counter" and member == "dn":
            return
        raise ValueError(f"{tag} is not compatible with a boolean instruction")

    def ensure_numeric_ref(tag: str) -> None:
        parts = split_timer_member(tag)
        if parts is None:
            variable = variable_map.get(tag)
            if variable is not None and variable.data_type not in {"int", "float"}:
                raise ValueError(f"{tag} is a {variable.data_type} variable and cannot be used in a numeric instruction")
            return
        base, member = parts
        variable = variable_map.get(base)
        if member not in {"acc", "pre"}:
            raise ValueError(f"{tag} is not a numeric member")
        if variable is None:
            return
        if variable.data_type not in {"timer", "counter"}:
            raise ValueError(f"{tag} is not compatible with a numeric instruction")

    def ensure_scalar_destination(tag: str) -> None:
        if split_timer_member(tag) is not None:
            raise ValueError(f"{tag} cannot be written by this instruction")
        variable = variable_map.get(tag)
        if variable is not None and variable.data_type not in {"int", "float"}:
            raise ValueError(f"{tag} is a {variable.data_type} variable and cannot be used as a numeric destination")

    def ensure_composite_tag(tag: str, expected_type: str) -> None:
        if split_timer_member(tag) is not None:
            raise ValueError(f"{tag} must use the base {expected_type} tag")
        variable = variable_map.get(tag)
        if variable is not None and variable.data_type != expected_type:
            raise ValueError(f"{tag} is a {variable.data_type} variable and cannot be used as a {expected_type}")

    if step.op in {"XIC", "XIO"}:
        ensure_boolean_ref(step.tag, allow_members=True)
        return
    if step.op in {"OTE", "OTL", "OTU"}:
        ensure_boolean_ref(step.tag, allow_members=False)
        return
    if step.op == "TON":
        ensure_composite_tag(step.tag, "timer")
        return
    if step.op in {"CTU", "CTD"}:
        ensure_composite_tag(step.tag, "counter")
        return
    if step.op == "CLR":
        if split_timer_member(step.tag) is not None:
            raise ValueError("CLR must target a base variable or composite tag")
        variable = variable_map.get(step.tag)
        if variable is not None and variable.data_type not in {"int", "float", "timer", "counter"}:
            raise ValueError(f"{step.tag} is a {variable.data_type} variable and cannot be cleared")
        return
    if step.op in {"MOV", "ABS", "NEG"}:
        ensure_scalar_destination(step.tag)
        source = step.params.get("source")
        if isinstance(source, str):
            ensure_numeric_ref(source)
        return
    if step.op in {"ADD", "SUB", "MUL", "DIV"}:
        ensure_scalar_destination(step.tag)
        for key in ("left", "right"):
            operand = step.params.get(key)
            if isinstance(operand, str):
                ensure_numeric_ref(operand)
        return
    if step.op in {"CMP", "EQ", "GT", "GTE", "LT", "LE", "NE"}:
        for key in ("left", "right"):
            operand = step.params.get(key)
            if isinstance(operand, str):
                ensure_numeric_ref(operand)


def default_tag_for_selection(selection: SelectionTarget | None, program: Program) -> str | None:
    if selection is None or selection.kind != "step" or selection.path is None:
        return None
    node = get_node_at_path(program.rungs[selection.rung_index].elements, selection.path)
    if isinstance(node, Step):
        return step_primary_tag(node)
    return None


class StepDialog(tk.Toplevel):
    COMPARISON_SYMBOLS = ["==", "!=", ">", ">=", "<", "<="]

    def __init__(self, parent: tk.Misc, *, title: str, initial: Step | None = None) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.configure(bg=PALETTE["panel"])
        self.resizable(False, False)
        self.result: Step | None = None

        self.op_var = tk.StringVar(value=initial.op if initial else "")
        self.tag_var = tk.StringVar(value=initial.tag if initial and initial.tag else "")
        self.arg_var = tk.StringVar(value=str(initial.arg) if initial and initial.arg is not None else "")
        self.source_var = tk.StringVar(value=self._initial_operand(initial, "source"))
        self.left_var = tk.StringVar(value=self._initial_operand(initial, "left"))
        self.right_var = tk.StringVar(value=self._initial_operand(initial, "right"))
        self.compare_var = tk.StringVar(value=str((initial.params.get("cmp") if initial else "") or "=="))
        self.filter_var = tk.StringVar(value=self.op_var.get())
        self.available_ops = [
            "XIC",
            "XIO",
            "CMP",
            "EQ",
            "GT",
            "GTE",
            "LT",
            "LE",
            "NE",
            "OTE",
            "OTL",
            "OTU",
            "TON",
            "CTU",
            "CTD",
            "MOV",
            "CLR",
            "ADD",
            "ABS",
            "MUL",
            "DIV",
            "NEG",
            "SUB",
        ]

        body = ttk.Frame(self, padding=12, style="Card.TFrame")
        body.grid(sticky="nsew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Instruction").grid(row=0, column=0, sticky="w", pady=(0, 8))
        self.filter_entry = ttk.Entry(body, textvariable=self.filter_var, width=28)
        self.filter_entry.grid(row=0, column=1, sticky="ew", pady=(0, 8))

        self.listbox = tk.Listbox(
            body,
            height=5,
            bg=PALETTE["panel_alt"],
            fg=PALETTE["text"],
            selectbackground=PALETTE["accent"],
            selectforeground=PALETTE["text"],
            highlightthickness=0,
            relief="flat",
        )
        self.listbox.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        self.listbox.bind("<<ListboxSelect>>", self._on_pick)
        self.listbox.bind("<Double-1>", lambda event: self.on_ok())

        self.tag_label = ttk.Label(body, text="Tag")
        self.tag_label.grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.tag_entry = ttk.Entry(body, textvariable=self.tag_var, width=28)
        self.tag_entry.grid(row=2, column=1, sticky="ew", pady=(0, 8))

        self.source_label = ttk.Label(body, text="Source")
        self.source_label.grid(row=3, column=0, sticky="w", pady=(0, 8))
        self.source_entry = ttk.Entry(body, textvariable=self.source_var, width=28)
        self.source_entry.grid(row=3, column=1, sticky="ew", pady=(0, 8))

        self.left_label = ttk.Label(body, text="Left")
        self.left_label.grid(row=4, column=0, sticky="w", pady=(0, 8))
        self.left_entry = ttk.Entry(body, textvariable=self.left_var, width=28)
        self.left_entry.grid(row=4, column=1, sticky="ew", pady=(0, 8))

        self.compare_label = ttk.Label(body, text="Compare")
        self.compare_label.grid(row=5, column=0, sticky="w", pady=(0, 8))
        self.compare_combo = ttk.Combobox(
            body,
            textvariable=self.compare_var,
            values=self.COMPARISON_SYMBOLS,
            state="readonly",
            width=10,
        )
        self.compare_combo.grid(row=5, column=1, sticky="w", pady=(0, 8))

        self.right_label = ttk.Label(body, text="Right")
        self.right_label.grid(row=6, column=0, sticky="w", pady=(0, 8))
        self.right_entry = ttk.Entry(body, textvariable=self.right_var, width=28)
        self.right_entry.grid(row=6, column=1, sticky="ew", pady=(0, 8))

        self.arg_label = ttk.Label(body, text="Preset")
        self.arg_label.grid(row=7, column=0, sticky="w")
        self.arg_entry = ttk.Entry(body, textvariable=self.arg_var, width=28)
        self.arg_entry.grid(row=7, column=1, sticky="ew")

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=8, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy, style="Tool.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="OK", command=self.on_ok, style="Accent.TButton").pack(side="right")

        self.filter_var.trace_add("write", lambda *_: self._refresh_list())
        self.op_var.trace_add("write", lambda *_: self._update_field_states())
        self._update_field_states()
        self._refresh_list()

        self.bind("<Return>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.destroy())
        self.grab_set()
        self.filter_entry.focus_set()
        self.wait_window(self)

    @staticmethod
    def _initial_operand(step: Step | None, key: str) -> str:
        if step is None:
            return ""
        value = step.params.get(key)
        if value is None:
            return ""
        return str(value)

    def _refresh_list(self) -> None:
        query = self.filter_var.get().strip().upper()
        items = [op for op in self.available_ops if not query or query in op]
        if not items:
            items = self.available_ops
        self.listbox.delete(0, "end")
        for item in items:
            self.listbox.insert("end", item)
        current = self.op_var.get().strip().upper()
        if current in items:
            index = items.index(current)
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            return
        if query:
            index = 0
            self.op_var.set(items[0])
            self.listbox.selection_set(index)
            self.listbox.activate(index)
            return
        self.op_var.set("")

    def _on_pick(self, event: object | None = None) -> None:
        selection = self.listbox.curselection()
        if not selection:
            return
        self.op_var.set(self.listbox.get(selection[0]))

    def _show_field(self, label: ttk.Label, entry: tk.Widget, enabled: bool, text: str) -> None:
        label.configure(text=text)
        if enabled:
            label.grid()
            entry.grid()
            if hasattr(entry, "state"):
                entry.state(["!disabled"])
        else:
            label.grid_remove()
            entry.grid_remove()
            if hasattr(entry, "state"):
                entry.state(["disabled"])

    def _update_field_states(self) -> None:
        op = self.op_var.get().strip().upper()

        show_tag = op in {"XIC", "XIO", "OTE", "OTL", "OTU", "TON", "CTU", "CTD", "MOV", "CLR", "ADD", "ABS", "MUL", "DIV", "NEG", "SUB"}
        tag_text = "Destination" if op in {"MOV", "ADD", "ABS", "MUL", "DIV", "NEG", "SUB"} else "Tag"
        if op == "TON":
            tag_text = "Timer tag"
        if op in {"CTU", "CTD"}:
            tag_text = "Counter tag"
        self._show_field(self.tag_label, self.tag_entry, show_tag, tag_text)

        self._show_field(self.source_label, self.source_entry, op in {"MOV", "ABS", "NEG"}, "Source")
        self._show_field(self.left_label, self.left_entry, op in {"CMP", "EQ", "GT", "GTE", "LT", "LE", "NE", "ADD", "MUL", "DIV", "SUB"}, "Left")
        self._show_field(self.right_label, self.right_entry, op in {"CMP", "EQ", "GT", "GTE", "LT", "LE", "NE", "ADD", "MUL", "DIV", "SUB"}, "Right")
        self._show_field(self.compare_label, self.compare_combo, op == "CMP", "Compare")
        self._show_field(self.arg_label, self.arg_entry, op in {"TON", "CTU", "CTD"}, "Preset (ms)" if op == "TON" else "Preset")

        if op not in {"TON", "CTU", "CTD"}:
            self.arg_var.set("")
        if op not in {"CMP"}:
            self.compare_var.set("==")

    def on_ok(self) -> None:
        try:
            chosen_op = self.op_var.get().strip().upper() or self.filter_var.get().strip().upper()
            if chosen_op not in self.available_ops:
                raise ValueError("Choose an instruction type")
            arg = int(self.arg_var.get()) if chosen_op in {"TON", "CTU", "CTD"} and self.arg_var.get().strip() else None
            step: Step
            if chosen_op in {"XIC", "XIO", "OTE", "OTL", "OTU", "TON", "CTU", "CTD", "CLR"}:
                step = Step(op=chosen_op, tag=self.tag_var.get().strip(), arg=arg)
            elif chosen_op in {"MOV", "ABS", "NEG"}:
                step = Step(
                    op=chosen_op,
                    tag=self.tag_var.get().strip(),
                    params={"source": parse_scalar_or_tag(self.source_var.get())},
                )
            elif chosen_op in {"ADD", "SUB", "MUL", "DIV"}:
                step = Step(
                    op=chosen_op,
                    tag=self.tag_var.get().strip(),
                    params={
                        "left": parse_scalar_or_tag(self.left_var.get()),
                        "right": parse_scalar_or_tag(self.right_var.get()),
                    },
                )
            elif chosen_op == "CMP":
                step = Step(
                    op=chosen_op,
                    params={
                        "left": parse_scalar_or_tag(self.left_var.get()),
                        "right": parse_scalar_or_tag(self.right_var.get()),
                        "cmp": self.compare_var.get().strip(),
                    },
                )
            else:
                step = Step(
                    op=chosen_op,
                    params={
                        "left": parse_scalar_or_tag(self.left_var.get()),
                        "right": parse_scalar_or_tag(self.right_var.get()),
                    },
                )
            step.validate()
        except Exception as exc:
            messagebox.showerror("Invalid instruction", str(exc), parent=self)
            return
        self.result = step
        self.destroy()


class BindingDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, *, title: str, initial: Binding | None = None) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.configure(bg=PALETTE["panel"])
        self.resizable(False, False)
        self.result: Binding | None = None

        self.tag_var = tk.StringVar(value=initial.tag if initial else "")
        self.direction_var = tk.StringVar(value=initial.direction if initial else "input")
        self.address_var = tk.StringVar(value=initial.address if initial else "")

        body = ttk.Frame(self, padding=12, style="Card.TFrame")
        body.grid(sticky="nsew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Tag").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(body, textvariable=self.tag_var, width=28).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Direction").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(body, textvariable=self.direction_var, values=["input", "output"], state="readonly").grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(0, 8),
        )

        ttk.Label(body, text="Address").grid(row=2, column=0, sticky="w")
        ttk.Entry(body, textvariable=self.address_var, width=28).grid(row=2, column=1, sticky="ew")

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy, style="Tool.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="OK", command=self.on_ok, style="Accent.TButton").pack(side="right")

        self.bind("<Return>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.destroy())
        self.grab_set()
        self.wait_window(self)

    def on_ok(self) -> None:
        try:
            binding = Binding(
                tag=self.tag_var.get().strip(),
                direction=self.direction_var.get().strip(),
                address=self.address_var.get().strip(),
            )
            binding.validate()
        except Exception as exc:
            messagebox.showerror("Invalid binding", str(exc), parent=self)
            return
        self.result = binding
        self.destroy()


class VariableDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, *, title: str, initial: Variable | None = None) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.configure(bg=PALETTE["panel"])
        self.resizable(False, False)
        self.result: Variable | None = None

        self.tag_var = tk.StringVar(value=initial.tag if initial else "")
        self.type_var = tk.StringVar(value=display_type_name(initial.data_type) if initial else "BOOL")
        seed_value = (
            str(initial.preset)
            if initial and initial.data_type in {"timer", "counter"}
            else (format_runtime_value(initial.initial) if initial and initial.initial is not None else "0")
        )
        self.value_var = tk.StringVar(value=seed_value)

        body = ttk.Frame(self, padding=12, style="Card.TFrame")
        body.grid(sticky="nsew")
        body.columnconfigure(1, weight=1)

        ttk.Label(body, text="Tag").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(body, textvariable=self.tag_var, width=28).grid(row=0, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Type").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Combobox(body, textvariable=self.type_var, values=["BOOL", "DINT", "REAL", "TIMER", "COUNTER"], state="readonly").grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(0, 8),
        )

        self.value_label = ttk.Label(body, text="Initial")
        self.value_label.grid(row=2, column=0, sticky="w")
        ttk.Entry(body, textvariable=self.value_var, width=28).grid(row=2, column=1, sticky="ew")

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=3, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy, style="Tool.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="OK", command=self.on_ok, style="Accent.TButton").pack(side="right")

        self.type_var.trace_add("write", lambda *_: self._update_value_label())
        self._update_value_label()

        self.bind("<Return>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.destroy())
        self.grab_set()
        self.wait_window(self)

    def _update_value_label(self) -> None:
        data_type = DISPLAY_TO_TYPE_NAMES.get(self.type_var.get().strip().upper(), "")
        self.value_label.configure(text="Preset" if data_type in {"timer", "counter"} else "Initial")

    def on_ok(self) -> None:
        try:
            data_type = DISPLAY_TO_TYPE_NAMES.get(self.type_var.get().strip().upper(), "")
            tag = self.tag_var.get().strip()
            if data_type == "bool":
                variable = Variable(tag=tag, data_type=data_type, initial=parse_bool(self.value_var.get()))
            elif data_type == "int":
                variable = Variable(tag=tag, data_type=data_type, initial=int(self.value_var.get().strip()))
            elif data_type == "float":
                variable = Variable(tag=tag, data_type=data_type, initial=float(self.value_var.get().strip()))
            elif data_type in {"timer", "counter"}:
                variable = Variable(tag=tag, data_type=data_type, preset=int(self.value_var.get().strip() or "0"))
            else:
                raise ValueError("Choose a tag type")
            variable.validate()
        except Exception as exc:
            messagebox.showerror("Invalid tag", str(exc), parent=self)
            return
        self.result = variable
        self.destroy()


class BindingsManagerDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, program: Program) -> None:
        super().__init__(parent)
        self.title("Bindings")
        self.transient(parent)
        self.configure(bg=PALETTE["panel"])
        self.program = program

        body = ttk.Frame(self, padding=12, style="Card.TFrame")
        body.pack(fill="both", expand=True)
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)

        ttk.Label(body, text="GPIO / I/O Bindings", style="Header.TLabel").grid(row=0, column=0, sticky="w")

        self.listbox = tk.Listbox(
            body,
            bg=PALETTE["panel_alt"],
            fg=PALETTE["text"],
            selectbackground=PALETTE["accent"],
            selectforeground=PALETTE["text"],
            highlightthickness=0,
            relief="flat",
            font=("TkDefaultFont", 11),
        )
        self.listbox.grid(row=1, column=0, sticky="nsew", pady=(10, 10))

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=2, column=0, sticky="ew")
        ttk.Button(buttons, text="Add", command=self.add_binding, style="Tool.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Edit", command=self.edit_binding, style="Tool.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Delete", command=self.delete_binding, style="Tool.TButton").pack(side="left")
        ttk.Button(buttons, text="Close", command=self.destroy, style="Accent.TButton").pack(side="right")

        self.refresh()

    def refresh(self) -> None:
        self.listbox.delete(0, "end")
        for binding in self.program.bindings:
            self.listbox.insert("end", f"{binding.tag}   {binding.direction}   {binding.address}")

    def current_index(self) -> int | None:
        selection = self.listbox.curselection()
        if not selection:
            return None
        return int(selection[0])

    def add_binding(self) -> None:
        dialog = BindingDialog(self, title="Add binding")
        if dialog.result is None:
            return
        self.program.bindings = [binding for binding in self.program.bindings if binding.tag != dialog.result.tag]
        self.program.bindings.append(dialog.result)
        self.refresh()

    def edit_binding(self) -> None:
        index = self.current_index()
        if index is None:
            return
        dialog = BindingDialog(self, title="Edit binding", initial=self.program.bindings[index])
        if dialog.result is None:
            return
        self.program.bindings[index] = dialog.result
        self.refresh()

    def delete_binding(self) -> None:
        index = self.current_index()
        if index is None:
            return
        self.program.bindings.pop(index)
        self.refresh()


def get_node_at_path(nodes: list[Node], path: tuple[int, ...]) -> Node:
    current_nodes = nodes
    cursor = 0
    while cursor < len(path) - 1:
        node_index = path[cursor]
        lane_index = path[cursor + 1]
        branch = current_nodes[node_index]
        if not isinstance(branch, Branch):
            raise ValueError("Invalid branch path")
        current_nodes = branch.lanes[lane_index]
        cursor += 2
    return current_nodes[path[-1]]


def resolve_parent_list(nodes: list[Node], path: tuple[int, ...]) -> tuple[list[Node], int]:
    current_nodes = nodes
    cursor = 0
    while cursor < len(path) - 1:
        node_index = path[cursor]
        lane_index = path[cursor + 1]
        branch = current_nodes[node_index]
        if not isinstance(branch, Branch):
            raise ValueError("Invalid branch path")
        current_nodes = branch.lanes[lane_index]
        cursor += 2
    return current_nodes, path[-1]


def normalize_nodes(nodes: list[Node]) -> list[Node]:
    normalized: list[Node] = []
    for node in nodes:
        if isinstance(node, Step):
            normalized.append(node)
            continue
        normalized_lanes = [normalize_nodes(lane) for lane in node.lanes]
        normalized_lanes = [lane for lane in normalized_lanes if lane]
        if not normalized_lanes:
            continue
        if len(normalized_lanes) == 1:
            normalized.extend(normalized_lanes[0])
            continue
        normalized.append(Branch(lanes=normalized_lanes))
    return normalized


def step_selection_key(rung_index: int, path: tuple[int, ...]) -> str:
    return f"step:{rung_index}:{'.'.join(str(part) for part in path)}"


def first_step_path(nodes: list[Node]) -> tuple[int, ...] | None:
    for index, node in enumerate(nodes):
        if isinstance(node, Step):
            return (index,)
        for lane_index, lane in enumerate(node.lanes):
            nested = first_step_path(lane)
            if nested is not None:
                return (index, lane_index, *nested)
    return None


def offline_live_locked(mode: str, simulation_state: str) -> bool:
    return mode == "offline" and simulation_state in {"running", "stepped"}


def default_serial_port() -> str:
    if list_ports is not None:
        try:
            devices = sorted(port.device for port in list_ports.comports())
            for token in ("usbserial", "usbmodem", "ttyUSB", "ttyACM"):
                for device in devices:
                    if token in device:
                        return device
            if devices:
                return devices[0]
        except Exception:
            pass
    return "/dev/ttyUSB0"


class PLCAsciiIDE:
    def __init__(self, program: Program | None = None, program_path: Path | None = None) -> None:
        self.root = tk.Tk()
        self.root.title("PLC ASCII IDE")
        self.root.geometry("1540x920")
        self.root.minsize(1180, 760)
        self.root.configure(bg=PALETTE["bg"])

        self.program = program or Program(name="untitled")
        self.program_path = program_path
        self.engine = LadderEngine(self.program)
        self.last_scan: ScanResult | None = None
        self.remote: RemoteSession | None = None
        self.remote_label: str | None = None
        self.remote_snapshot: dict[str, object] = {}
        self.remote_watch_job: str | None = None
        self.run_job: str | None = None
        self.current_document: RenderedDocument | None = None
        self.selected_key: str | None = None
        self.selection_tag_to_key: dict[str, str] = {}
        self.help_text: tk.Text | None = None
        self.step_button: ttk.Button | None = None
        self.run_button: ttk.Button | None = None
        self.stop_button: ttk.Button | None = None
        self.download_button: ttk.Button | None = None
        self.font_label_widget: ttk.Label | None = None
        self.disconnect_button: ttk.Button | None = None
        self.reset_button: ttk.Checkbutton | None = None
        self.scan_label_widget: ttk.Label | None = None
        self.scan_spinbox_widget: ttk.Spinbox | None = None
        self.tooltip_text_by_widget: dict[str, str] = {}
        self.tooltip_job: str | None = None
        self.tooltip_window: tk.Toplevel | None = None
        self.tooltip_label: tk.Label | None = None
        self.tooltip_widget: tk.Misc | None = None
        self.simulation_state = "stopped"
        self.monitor_tree: ttk.Treeview | None = None

        self.mode_var = tk.StringVar(value="offline")
        self.status_var = tk.StringVar(value="Offline programming / simulation")
        self.auto_online_var = tk.BooleanVar(value=False)
        self.help_var = tk.BooleanVar(value=False)
        self.reset_integer_var = tk.BooleanVar(value=True)
        self.scan_ms_var = tk.IntVar(value=100)
        self.font_size_var = tk.IntVar(value=18)
        self.connection_var = tk.StringVar(value="Board: Disconnected")
        self.last_serial_port = default_serial_port()
        self.last_serial_baud = 115200

        self.fixed_font = font.nametofont("TkFixedFont").copy()
        self.fixed_font.configure(size=self.font_size_var.get())

        self._apply_theme()
        self._build_menu()
        self._build_layout()
        self.sync_program_variables(save_current_values=False)
        self.update_connection_indicator()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(50, self.render_ladder)

    def _apply_theme(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=PALETTE["bg"], foreground=PALETTE["text"])
        style.configure("TFrame", background=PALETTE["bg"])
        style.configure("Card.TFrame", background=PALETTE["panel"])
        style.configure("TLabel", background=PALETTE["bg"], foreground=PALETTE["text"])
        style.configure("Header.TLabel", background=PALETTE["bg"], foreground=PALETTE["text"], font=("TkDefaultFont", 12, "bold"))
        style.configure("Subtle.TLabel", background=PALETTE["bg"], foreground=PALETTE["muted"])
        style.configure("TButton", background=PALETTE["panel_alt"], foreground=PALETTE["text"], padding=(10, 7), borderwidth=0)
        style.map("TButton", background=[("active", PALETTE["border"]), ("pressed", PALETTE["accent"])])
        style.configure("Tool.TButton", background=PALETTE["panel"], foreground=PALETTE["text"])
        style.map("Tool.TButton", background=[("active", PALETTE["panel_alt"])])
        style.configure("Accent.TButton", background=PALETTE["accent"], foreground=PALETTE["text"], font=("TkDefaultFont", 10, "bold"))
        style.map("Accent.TButton", background=[("active", "#ff7569"), ("pressed", "#ef5044")])
        style.configure("ActionOff.TButton", background=PALETTE["accent"], foreground=PALETTE["text"], font=("TkDefaultFont", 10, "bold"))
        style.map("ActionOff.TButton", background=[("active", "#ff7569"), ("pressed", "#ef5044")])
        style.configure("ActionOn.TButton", background=PALETTE["success"], foreground=PALETTE["text"], font=("TkDefaultFont", 10, "bold"))
        style.map("ActionOn.TButton", background=[("active", "#58d59a"), ("pressed", "#3aad79")])
        style.configure("TEntry", fieldbackground=PALETTE["panel_alt"], foreground=PALETTE["text"], insertcolor=PALETTE["text"])
        style.configure("TCombobox", fieldbackground=PALETTE["panel_alt"], background=PALETTE["panel_alt"], foreground=PALETTE["text"], arrowcolor=PALETTE["text"])
        style.configure("TRadiobutton", background=PALETTE["bg"], foreground=PALETTE["text"])
        style.configure("TCheckbutton", background=PALETTE["bg"], foreground=PALETTE["text"])
        style.configure("TSpinbox", fieldbackground=PALETTE["panel_alt"], foreground=PALETTE["text"])
        style.configure(
            "Treeview",
            background=PALETTE["panel_alt"],
            fieldbackground=PALETTE["panel_alt"],
            foreground=PALETTE["text"],
            borderwidth=0,
            rowheight=24,
        )
        style.map("Treeview", background=[("selected", PALETTE["accent"])], foreground=[("selected", PALETTE["text"])])
        style.configure("Treeview.Heading", background=PALETTE["panel"], foreground=PALETTE["text"], relief="flat")
        style.map("Treeview.Heading", background=[("active", PALETTE["border"])])

    def _build_menu(self) -> None:
        menu = tk.Menu(self.root, bg=PALETTE["panel"], fg=PALETTE["text"], activebackground=PALETTE["accent"], activeforeground=PALETTE["text"], bd=0)
        file_menu = tk.Menu(menu, tearoff=False, bg=PALETTE["panel"], fg=PALETTE["text"], activebackground=PALETTE["accent"], activeforeground=PALETTE["text"])
        file_menu.add_command(label="New", command=self.new_program)
        file_menu.add_command(label="Open...", command=self.open_program)
        file_menu.add_command(label="Save", command=self.save_program)
        file_menu.add_command(label="Save As...", command=self.save_program_as)
        file_menu.add_separator()
        file_menu.add_command(label="Bindings...", command=self.manage_bindings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menu.add_cascade(label="File", menu=file_menu)

        remote_menu = tk.Menu(menu, tearoff=False, bg=PALETTE["panel"], fg=PALETTE["text"], activebackground=PALETTE["accent"], activeforeground=PALETTE["text"])
        remote_menu.add_command(label="Install Runtime to CircuitPython...", command=self.install_circuitpython_runtime)
        remote_menu.add_separator()
        remote_menu.add_command(label="Download", command=self.remote_download_program)
        remote_menu.add_command(label="Upload", command=self.remote_upload_program)
        remote_menu.add_command(label="Go Online", command=self.go_online)
        remote_menu.add_command(label="Disconnect", command=self.disconnect_remote)
        menu.add_cascade(label="Runtime", menu=remote_menu)

        debug_menu = tk.Menu(menu, tearoff=False, bg=PALETTE["panel"], fg=PALETTE["text"], activebackground=PALETTE["accent"], activeforeground=PALETTE["text"])
        debug_menu.add_command(label="Set Tag", command=self.set_tag_dialog)
        debug_menu.add_command(label="Force Tag", command=self.force_tag_dialog)
        debug_menu.add_command(label="Unforce Tag", command=self.unforce_tag_dialog)
        debug_menu.add_command(label="Edit Comment", command=self.edit_rung_comment)
        menu.add_cascade(label="Debug", menu=debug_menu)

        help_menu = tk.Menu(menu, tearoff=False, bg=PALETTE["panel"], fg=PALETTE["text"], activebackground=PALETTE["accent"], activeforeground=PALETTE["text"])
        help_menu.add_command(label="Documentation", command=self.open_docs_document)
        help_menu.add_command(label="README", command=self.open_readme_document)
        help_menu.add_command(label="GUI Help", command=self.open_help_document)
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menu)

    @staticmethod
    def markdown_viewer_css(body_font_px: int) -> str:
        body_font_px = max(14, min(30, int(body_font_px)))
        return (
            MARKDOWN_VIEWER_CSS
            .replace("__BODY_FONT_PX__", str(body_font_px))
            .replace("__H1_FONT_PX__", str(round(body_font_px * 2.0)))
            .replace("__H2_FONT_PX__", str(round(body_font_px * 1.6)))
            .replace("__H3_FONT_PX__", str(round(body_font_px * 1.3)))
            .replace("__H4_FONT_PX__", str(round(body_font_px * 1.15)))
        )

    def render_markdown_document(self, path: Path, body_font_px: int = 20) -> str:
        if not path.exists():
            raise FileNotFoundError(f"Missing document: {path}")
        markdown_text = path.read_text(encoding="utf-8")
        html_body = markdown.markdown(
            markdown_text,
            extensions=["fenced_code", "tables", "toc", "sane_lists"],
        )
        title = path.name
        return (
            "<!DOCTYPE html>"
            "<html><head>"
            f"<meta charset='utf-8'><title>{title}</title>"
            f"<style>{self.markdown_viewer_css(body_font_px)}</style>"
            "</head><body>"
            f"{html_body}"
            "</body></html>"
        )

    def open_markdown_document(self, title: str, path: Path) -> None:
        window = tk.Toplevel(self.root)
        window.title(title)
        window.geometry("1120x780")
        window.minsize(840, 620)
        window.configure(bg=PALETTE["bg"])

        header = ttk.Frame(window, style="Card.TFrame", padding=(12, 10, 12, 10))
        header.pack(fill="x")
        ttk.Label(header, text=title, style="Header.TLabel").pack(side="left")
        ttk.Label(header, text=str(path.relative_to(REPO_ROOT)), style="Subtle.TLabel").pack(side="left", padx=(10, 0))
        font_px_var = tk.IntVar(value=20)

        viewer = HtmlFrame(window, messages_enabled=False)
        viewer.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        zoom_controls = ttk.Frame(header, style="Card.TFrame")
        zoom_controls.pack(side="right")
        ttk.Label(zoom_controls, text="Text", style="Subtle.TLabel").pack(side="left", padx=(0, 8))
        font_value_label = ttk.Label(zoom_controls, textvariable=font_px_var, style="Subtle.TLabel", width=3)
        ttk.Button(zoom_controls, text="A-", style="Tool.TButton").pack(side="left", padx=(0, 6))
        ttk.Button(zoom_controls, text="A+", style="Tool.TButton").pack(side="left")
        font_value_label.pack(side="left", padx=(8, 0))

        def refresh_view() -> None:
            try:
                html = self.render_markdown_document(path, body_font_px=font_px_var.get())
            except Exception as exc:
                messagebox.showerror("Documentation failed", str(exc), parent=window)
                window.destroy()
                return
            viewer.load_html(html, base_url=path.parent.as_uri())

        def adjust_font(delta: int) -> None:
            font_px_var.set(max(14, min(30, font_px_var.get() + delta)))
            refresh_view()

        zoom_buttons = [child for child in zoom_controls.winfo_children() if isinstance(child, ttk.Button)]
        zoom_buttons[0].configure(command=lambda: adjust_font(-2))
        zoom_buttons[1].configure(command=lambda: adjust_font(2))

        refresh_view()

    def open_docs_document(self) -> None:
        self.open_markdown_document("PLC ASCII Documentation", DOCS_PATH)

    def open_readme_document(self) -> None:
        self.open_markdown_document("PLC ASCII README", README_PATH)

    def open_help_document(self) -> None:
        self.open_markdown_document("PLC ASCII Help", HELP_PATH)

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=(12, 10, 12, 12), style="Card.TFrame")
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(outer, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.step_button = ttk.Button(toolbar, text="Step", command=self.step_scan, style="ActionOff.TButton")
        self.step_button.pack(side="left", padx=(0, 8))
        self.register_tooltip(self.step_button, "Execute one offline PLC scan and retain values until Run or Stop is pressed.")

        self.run_button = ttk.Button(toolbar, text="Run", command=self.start_run, style="ActionOff.TButton")
        self.run_button.pack(side="left", padx=(0, 8))
        self.register_tooltip(self.run_button, "Start continuous offline simulation scans.")

        stop_button = ttk.Button(toolbar, text="Stop", command=self.stop_run, style="Tool.TButton")
        stop_button.pack(side="left", padx=(0, 8))
        self.register_tooltip(
            stop_button,
            "Stop ends offline simulation. Boolean logic drops out, timers/counters reset, and Reset Integer controls whether numeric tags are cleared to zero. Press Stop again while already stopped to clear forces too.",
        )
        self.stop_button = stop_button

        download_button = ttk.Button(toolbar, text="Download", command=self.remote_download_program, style="Tool.TButton")
        download_button.pack(side="left", padx=(0, 8))
        self.register_tooltip(download_button, "Connect to the board if needed, then send the current ladder program to it.")
        self.download_button = download_button

        upload_button = ttk.Button(toolbar, text="Upload", command=self.remote_upload_program, style="Tool.TButton")
        upload_button.pack(side="left", padx=(0, 8))
        self.register_tooltip(upload_button, "Connect to the board if needed, then read the stored ladder program back into the IDE.")

        go_online_button = ttk.Button(toolbar, text="Go Online", command=self.go_online, style="Accent.TButton")
        go_online_button.pack(side="left", padx=(0, 8))
        self.register_tooltip(go_online_button, "Connect to the board if needed, switch to online mode, and start continuous live monitoring.")

        disconnect_button = ttk.Button(toolbar, text="Disconnect", command=self.disconnect_remote, style="Tool.TButton")
        disconnect_button.pack(side="left", padx=(0, 8))
        self.register_tooltip(disconnect_button, "Disconnect from the board, stop live monitoring, and return to offline editing.")
        self.disconnect_button = disconnect_button

        connection_label = tk.Label(
            toolbar,
            textvariable=self.connection_var,
            bg=PALETTE["panel"],
            fg=PALETTE["danger"],
            padx=10,
            pady=4,
        )
        connection_label.pack(side="left", padx=(14, 8))
        self.register_tooltip(connection_label, "Shows whether the IDE is currently connected to the board over serial.")
        self.connection_label = connection_label

        help_button = ttk.Checkbutton(toolbar, text="Help", variable=self.help_var, command=self.update_help_visibility)
        help_button.pack(side="left", padx=(12, 0))
        self.register_tooltip(help_button, "Show keyboard shortcuts below and enable hover tooltips.")

        reset_button = ttk.Checkbutton(toolbar, text="Reset Integer", variable=self.reset_integer_var)
        reset_button.pack(side="left", padx=(12, 0))
        self.register_tooltip(
            reset_button,
            "When checked, Stop restores monitor start values for scalars and clears timer/counter accumulators while preserving presets.",
        )
        self.reset_button = reset_button

        scan_label = ttk.Label(toolbar, text="Scan", style="Subtle.TLabel")
        scan_label.pack(side="left", padx=(14, 6))
        self.register_tooltip(scan_label, "Offline scan period in milliseconds.")
        self.scan_label_widget = scan_label

        scan_spinbox = ttk.Spinbox(toolbar, from_=10, to=5000, increment=10, textvariable=self.scan_ms_var, width=7)
        scan_spinbox.pack(side="left")
        self.register_tooltip(scan_spinbox, "Set the offline scan time in milliseconds.")
        self.scan_spinbox_widget = scan_spinbox

        font_label = ttk.Label(toolbar, text="Font", style="Subtle.TLabel")
        font_label.pack(side="left", padx=(14, 6))
        self.register_tooltip(font_label, "Ladder text size.")
        self.font_label_widget = font_label

        font_spinbox = ttk.Spinbox(toolbar, from_=12, to=30, increment=1, textvariable=self.font_size_var, width=5, command=self.update_font_size)
        font_spinbox.pack(side="left")
        self.register_tooltip(font_spinbox, "Increase or decrease the ladder viewer font size.")

        viewer = ttk.Frame(outer, style="Card.TFrame")
        viewer.grid(row=1, column=0, sticky="nsew")
        viewer.rowconfigure(0, weight=1)
        viewer.columnconfigure(0, weight=4)
        viewer.columnconfigure(2, weight=2)

        self.ladder_text = tk.Text(
            viewer,
            wrap="none",
            font=self.fixed_font,
            bg=PALETTE["panel_alt"],
            fg=PALETTE["text"],
            insertbackground=PALETTE["text"],
            selectbackground=PALETTE["accent"],
            selectforeground=PALETTE["text"],
            relief="flat",
            highlightthickness=0,
            padx=18,
            pady=18,
            undo=False,
        )
        self.ladder_text.grid(row=0, column=0, sticky="nsew")
        self.ladder_text.bind("<Button-1>", self.on_click)
        self.ladder_text.bind("<Double-1>", self.on_double_click)
        self.ladder_text.bind("<Key>", self.on_key_press)
        self.ladder_text.bind("<FocusIn>", lambda event: self.ladder_text.mark_set("insert", "1.0"))
        self.register_tooltip(self.ladder_text, "Click to select a rung or instruction. Use the keyboard shortcuts below to edit it.")

        y_scroll = ttk.Scrollbar(viewer, orient="vertical", command=self.ladder_text.yview)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll = ttk.Scrollbar(viewer, orient="horizontal", command=self.ladder_text.xview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.ladder_text.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        monitor = ttk.Frame(viewer, style="Card.TFrame", padding=(10, 10, 10, 10))
        monitor.grid(row=0, column=2, rowspan=2, sticky="nsew", padx=(10, 0))
        monitor.rowconfigure(1, weight=1)
        monitor.columnconfigure(0, weight=1)

        monitor_header = ttk.Frame(monitor, style="Card.TFrame")
        monitor_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        monitor_header.columnconfigure(0, weight=1)
        ttk.Label(monitor_header, text="Monitor", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        add_var_button = ttk.Button(monitor_header, text="Add Tag", command=self.add_monitor_variable, style="Tool.TButton")
        add_var_button.grid(row=0, column=1, sticky="e")
        self.register_tooltip(add_var_button, "Add a monitored tag declaration and choose its type.")
        delete_var_button = ttk.Button(monitor_header, text="Delete Tag", command=self.delete_monitor_variable, style="Tool.TButton")
        delete_var_button.grid(row=0, column=2, sticky="e", padx=(6, 0))
        self.register_tooltip(delete_var_button, "Delete the selected tag. If it is used in the program, its instructions can be removed too.")

        self.monitor_tree = ttk.Treeview(monitor, columns=("value", "type"), show="tree headings")
        self.monitor_tree.heading("#0", text="Tag")
        self.monitor_tree.heading("value", text="Value")
        self.monitor_tree.heading("type", text="Type")
        self.monitor_tree.column("#0", width=170, anchor="w")
        self.monitor_tree.column("value", width=100, anchor="w")
        self.monitor_tree.column("type", width=90, anchor="w")
        self.monitor_tree.grid(row=1, column=0, sticky="nsew")
        self.monitor_tree.bind("<Double-1>", self.on_monitor_double_click)
        self.register_tooltip(self.monitor_tree, "Watch tags here. Double-click a value to edit it while stopped or stepped offline.")

        monitor_scroll = ttk.Scrollbar(monitor, orient="vertical", command=self.monitor_tree.yview)
        monitor_scroll.grid(row=1, column=1, sticky="ns")
        self.monitor_tree.configure(yscrollcommand=monitor_scroll.set)

        status = ttk.Label(outer, textvariable=self.status_var, style="Subtle.TLabel", anchor="w")
        status.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        self.help_text = tk.Text(
            outer,
            height=3,
            wrap="word",
            font=("TkDefaultFont", 10),
            bg=PALETTE["bg"],
            fg=PALETTE["text"],
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            padx=0,
            pady=0,
        )
        self.help_text.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.render_help_text()
        self.update_help_visibility()
        self.update_simulation_buttons()
        self.update_toolbar_visibility()

    def ensure_rung(self) -> int:
        if not self.program.rungs:
            self.program.rungs.append(Rung(comment="", elements=[]))
        return 0

    def current_selection(self) -> SelectionTarget | None:
        if self.current_document is None or self.selected_key is None:
            return None
        return self.current_document.selections.get(self.selected_key)

    def current_rung_index(self) -> int:
        selection = self.current_selection()
        if selection is not None:
            return selection.rung_index
        return self.ensure_rung()

    def is_live_locked(self) -> bool:
        return offline_live_locked(self.mode_var.get(), self.simulation_state)

    def sync_program_variables(self, save_current_values: bool) -> None:
        current_values = dict(self.engine.tags) if save_current_values else None
        populate_program_variables(self.program, current_values=current_values)
        self.engine.load_program(self.program)

    def validate_step_type_compatibility(self, step: Step) -> None:
        validate_program_step_types(self.program, step)

    def ensure_live_editable(self) -> bool:
        if self.is_live_locked():
            self.status_var.set("Stop simulation before editing or interacting with the ladder.")
            return False
        return True

    def is_monitor_editable(self) -> bool:
        return self.mode_var.get() == "offline" and self.simulation_state != "running"

    def ensure_monitor_editable(self) -> bool:
        if not self.is_monitor_editable():
            self.status_var.set("Monitor values can only be edited while offline and stopped or stepped.")
            return False
        return True

    def find_variable(self, tag: str) -> Variable | None:
        for variable in self.program.variables:
            if variable.tag == tag:
                return variable
        return None

    def upsert_variable(self, variable: Variable) -> None:
        for index, current in enumerate(self.program.variables):
            if current.tag == variable.tag:
                self.program.variables[index] = variable
                return
        self.program.variables.append(variable)

    def ensure_scalar_variable(self, tag: str, value: bool | int | float) -> None:
        variable = self.find_variable(tag)
        if variable is None:
            variable = Variable(tag=tag, data_type=infer_scalar_type(value), initial=value)
        else:
            variable.data_type = infer_scalar_type(value)
            variable.initial = value
            variable.preset = None
        variable.validate()
        self.upsert_variable(variable)

    def ensure_composite_variable(self, tag: str, data_type: str, preset: int) -> None:
        variable = self.find_variable(tag) or Variable(tag=tag, data_type=data_type, preset=preset)
        variable.data_type = data_type
        variable.initial = None
        variable.preset = int(preset)
        variable.validate()
        self.upsert_variable(variable)

    def inferred_monitor_types(self) -> dict[str, str]:
        inferred, _, _ = infer_program_variable_types(self.program)
        return inferred

    def current_monitor_snapshot(
        self,
    ) -> tuple[dict[str, object], dict[str, dict[str, object]], dict[str, dict[str, object]], set[str]]:
        if self.mode_var.get() == "online":
            tags = self.remote_snapshot.get("tags", {}) if isinstance(self.remote_snapshot, dict) else {}
            timers = self.remote_snapshot.get("timers", {}) if isinstance(self.remote_snapshot, dict) else {}
            counters = self.remote_snapshot.get("counters", {}) if isinstance(self.remote_snapshot, dict) else {}
            forced = self.remote_snapshot.get("forced", {}) if isinstance(self.remote_snapshot, dict) else {}
            return (
                tags if isinstance(tags, dict) else {},
                timers if isinstance(timers, dict) else {},
                counters if isinstance(counters, dict) else {},
                set(forced.keys()) if isinstance(forced, dict) else set(),
            )
        return (
            dict(self.engine.tags),
            {name: timer.snapshot() for name, timer in self.engine.timers.items()},
            {name: counter.snapshot() for name, counter in self.engine.counters.items()},
            set(self.engine.forced.keys()),
        )

    def render_monitor(self) -> None:
        if self.monitor_tree is None:
            return
        open_state = {item: self.monitor_tree.item(item, "open") for item in self.monitor_tree.get_children("")}
        for item in self.monitor_tree.get_children(""):
            for child in self.monitor_tree.get_children(item):
                open_state[child] = self.monitor_tree.item(child, "open")

        self.monitor_tree.delete(*self.monitor_tree.get_children(""))
        tags, timers, counters, forced_tags = self.current_monitor_snapshot()
        inferred = self.inferred_monitor_types()
        variable_map = self.program.variable_map()

        groups = {
            "bool": self.monitor_tree.insert("", "end", iid="group:bool", text="BOOL", values=("", "group"), open=True),
            "int": self.monitor_tree.insert("", "end", iid="group:int", text="DINT", values=("", "group"), open=True),
            "float": self.monitor_tree.insert("", "end", iid="group:float", text="REAL", values=("", "group"), open=True),
            "timer": self.monitor_tree.insert("", "end", iid="group:timer", text="TIMER", values=("", "group"), open=True),
            "counter": self.monitor_tree.insert("", "end", iid="group:counter", text="COUNTER", values=("", "group"), open=True),
        }

        scalar_rows: dict[str, tuple[str, object]] = {}
        for variable in self.program.variables:
            if variable.data_type in {"bool", "int", "float"}:
                scalar_rows[variable.tag] = (variable.data_type, tags.get(variable.tag, variable.initial if variable.initial is not None else 0))

        for tag, value in tags.items():
            if "." in tag:
                continue
            if tag in timers or tag in counters:
                continue
            data_type = variable_map.get(tag).data_type if tag in variable_map else inferred.get(tag, infer_scalar_type(value if isinstance(value, (bool, int, float)) else 0))
            if data_type in {"bool", "int", "float"}:
                scalar_rows[tag] = (data_type, value)

        for tag in sorted(scalar_rows):
            data_type, value = scalar_rows[tag]
            prefix = "f " if tag in forced_tags else ""
            self.monitor_tree.insert(
                groups[data_type],
                "end",
                iid=f"scalar:{tag}",
                text=f"{prefix}{tag}",
                values=(format_runtime_value(value if isinstance(value, (bool, int, float)) else 0), display_type_name(data_type)),
            )

        for tag in sorted(set(timers) | {name for name, variable in variable_map.items() if variable.data_type == "timer"}):
            timer = timers.get(tag, {"pre": variable_map[tag].preset if tag in variable_map else 0, "acc": 0, "en": False, "dn": False, "tt": False})
            parent = self.monitor_tree.insert(groups["timer"], "end", iid=f"timer:{tag}", text=tag, values=("", "TIMER"), open=open_state.get(f"timer:{tag}", False))
            for member in ("pre", "acc", "en", "dn", "tt"):
                value = timer.get(member, 0)
                member_type = "bool" if member in {"en", "dn", "tt"} else "int"
                self.monitor_tree.insert(
                    parent,
                    "end",
                    iid=f"member:timer:{tag}:{member}",
                    text=f".{member}",
                    values=(format_runtime_value(value if isinstance(value, (bool, int, float)) else 0), display_type_name(member_type)),
                )

        for tag in sorted(set(counters) | {name for name, variable in variable_map.items() if variable.data_type == "counter"}):
            counter = counters.get(tag, {"pre": variable_map[tag].preset if tag in variable_map else 0, "acc": 0, "dn": False})
            parent = self.monitor_tree.insert(groups["counter"], "end", iid=f"counter:{tag}", text=tag, values=("", "COUNTER"), open=open_state.get(f"counter:{tag}", False))
            for member in ("pre", "acc", "dn"):
                value = counter.get(member, 0)
                member_type = "bool" if member == "dn" else "int"
                self.monitor_tree.insert(
                    parent,
                    "end",
                    iid=f"member:counter:{tag}:{member}",
                    text=f".{member}",
                    values=(format_runtime_value(value if isinstance(value, (bool, int, float)) else 0), display_type_name(member_type)),
                )

    def add_monitor_variable(self) -> None:
        if not self.ensure_monitor_editable():
            return
        dialog = VariableDialog(self.root, title="Add tag")
        if dialog.result is None:
            return
        self.upsert_variable(dialog.result)
        self.engine.load_program(self.program)
        if dialog.result.data_type in {"bool", "int", "float"} and dialog.result.initial is not None:
            self.engine.set_value(dialog.result.tag, dialog.result.initial)
        self.last_scan = None
        self.status_var.set(f"Added tag {dialog.result.tag}")
        self.render_ladder()

    def selected_monitor_base_tag(self) -> str | None:
        if self.monitor_tree is None:
            return None
        selection = self.monitor_tree.selection()
        if not selection:
            return None
        item_id = selection[0]
        if item_id.startswith("scalar:"):
            return item_id.split(":", 1)[1]
        if item_id.startswith("timer:") or item_id.startswith("counter:"):
            return item_id.split(":", 1)[1]
        if item_id.startswith("member:"):
            _, _, tag, _ = item_id.split(":", 3)
            return tag
        return None

    @staticmethod
    def step_uses_variable(step: Step, tag: str) -> bool:
        if step.tag == tag or step.tag.startswith(f"{tag}."):
            return True
        for operand in step.params.values():
            if isinstance(operand, str) and (operand == tag or operand.startswith(f"{tag}.")):
                return True
        return False

    def variable_used_in_program(self, tag: str) -> bool:
        for rung in self.program.rungs:
            for step in walk_steps(rung.elements):
                if self.step_uses_variable(step, tag):
                    return True
        return False

    def remove_variable_from_nodes(self, nodes: list[Node], tag: str) -> list[Node]:
        kept: list[Node] = []
        for node in nodes:
            if isinstance(node, Step):
                if not self.step_uses_variable(node, tag):
                    kept.append(node)
                continue
            filtered_lanes = [self.remove_variable_from_nodes(lane, tag) for lane in node.lanes]
            filtered_lanes = [lane for lane in filtered_lanes if lane]
            if not filtered_lanes:
                continue
            if len(filtered_lanes) == 1:
                kept.extend(filtered_lanes[0])
                continue
            kept.append(Branch(lanes=filtered_lanes))
        return kept

    def delete_monitor_variable(self) -> None:
        if not self.ensure_monitor_editable():
            return
        tag = self.selected_monitor_base_tag()
        if not tag:
            return
        used = self.variable_used_in_program(tag)
        if used:
            confirm = messagebox.askyesno(
                "Delete tag",
                f"{tag} is used in the program. Delete it and remove all instructions that use it?",
                parent=self.root,
            )
            if not confirm:
                return
            for rung in self.program.rungs:
                rung.elements = normalize_nodes(self.remove_variable_from_nodes(rung.elements, tag))
        self.program.variables = [variable for variable in self.program.variables if variable.tag != tag]
        self.program.bindings = [binding for binding in self.program.bindings if binding.tag != tag]
        for forced_tag in list(self.engine.forced):
            if forced_tag == tag or forced_tag.startswith(f"{tag}."):
                self.engine.clear_force(forced_tag)
        self.sync_program_variables(save_current_values=True)
        self.last_scan = None
        self.status_var.set(f"Deleted tag {tag}")
        self.render_ladder()

    def on_monitor_double_click(self, event: tk.Event[ttk.Treeview]) -> str:
        self.edit_monitor_value()
        return "break"

    def edit_monitor_value(self) -> None:
        if self.monitor_tree is None:
            return
        selection = self.monitor_tree.selection()
        if not selection:
            return
        item_id = selection[0]
        if item_id.startswith("group:") or item_id.startswith("timer:") or item_id.startswith("counter:"):
            return
        if not self.ensure_monitor_editable():
            return

        if item_id.startswith("scalar:"):
            tag = item_id.split(":", 1)[1]
            current_value = self.engine.read_tag(tag)
            variable = self.find_variable(tag)
            data_type = variable.data_type if variable is not None else infer_scalar_type(current_value if isinstance(current_value, (bool, int, float)) else 0)
            if data_type == "bool":
                value = not bool(current_value)
            elif data_type == "float":
                raw = simpledialog.askstring("Monitor value", f"Value for {tag}", parent=self.root, initialvalue=format_runtime_value(float(current_value)))
                value = None if raw is None else float(raw.strip())
            else:
                value = simpledialog.askinteger("Monitor value", f"Value for {tag}", parent=self.root, initialvalue=int(current_value))
            if value is None:
                return
            self.engine.set_value(tag, value)
            self.ensure_scalar_variable(tag, value)
        elif item_id.startswith("member:"):
            _, composite_type, tag, member = item_id.split(":", 3)
            full_tag = f"{tag}.{member}"
            current_value = self.engine.read_tag(full_tag)
            if member in {"dn", "en", "tt"}:
                value = not bool(current_value)
            else:
                value = simpledialog.askinteger("Monitor value", f"Value for {full_tag}", parent=self.root, initialvalue=int(current_value))
            if value is None:
                return
            self.engine.set_value(full_tag, value)
            if member == "pre":
                self.ensure_composite_variable(tag, composite_type, int(value))
        else:
            return

        self.last_scan = None
        self.status_var.set("Updated monitor value")
        self.render_ladder()

    def on_mode_change(self) -> None:
        if self.mode_var.get() == "online":
            self.status_var.set("Online view selected")
        else:
            self.status_var.set("Offline programming / simulation")
        self.update_connection_indicator()
        self.update_toolbar_visibility()
        self.render_ladder()

    @staticmethod
    def set_toolbar_widget_visible(
        widget: tk.Misc | None,
        visible: bool,
        *,
        padx: tuple[int, int] | None = None,
        before: tk.Misc | None = None,
    ) -> None:
        if widget is None:
            return
        if visible:
            if not widget.winfo_manager():
                pack_kwargs: dict[str, object] = {"side": "left"}
                if padx is not None:
                    pack_kwargs["padx"] = padx
                if before is not None:
                    pack_kwargs["before"] = before
                widget.pack(**pack_kwargs)
            return
        if widget.winfo_manager():
            widget.pack_forget()

    def update_toolbar_visibility(self) -> None:
        offline_mode = self.mode_var.get() != "online"
        online_connected = self.mode_var.get() == "online" and self.remote is not None
        self.set_toolbar_widget_visible(self.step_button, offline_mode, padx=(0, 8), before=self.download_button)
        self.set_toolbar_widget_visible(self.run_button, offline_mode, padx=(0, 8), before=self.download_button)
        self.set_toolbar_widget_visible(self.stop_button, offline_mode, padx=(0, 8), before=self.download_button)
        self.set_toolbar_widget_visible(self.reset_button, offline_mode, padx=(12, 0), before=self.scan_label_widget)
        self.set_toolbar_widget_visible(self.scan_label_widget, offline_mode, padx=(14, 6), before=self.font_label_widget)
        self.set_toolbar_widget_visible(self.scan_spinbox_widget, offline_mode, before=self.font_label_widget)
        self.set_toolbar_widget_visible(self.disconnect_button, online_connected, padx=(0, 8), before=self.connection_label)

    def update_connection_indicator(self) -> None:
        if not hasattr(self, "connection_label"):
            return
        if self.remote is None:
            self.connection_var.set("Board: Disconnected")
            self.connection_label.configure(fg=PALETTE["danger"])
            return
        label = self.remote_label or "serial target"
        mode_text = "Online" if self.mode_var.get() == "online" else "Connected"
        self.connection_var.set(f"Board: {mode_text} ({label})")
        self.connection_label.configure(fg=PALETTE["success"])

    def start_remote_watch(self) -> None:
        self.auto_online_var.set(True)
        if self.remote_watch_job is None:
            self._remote_watch_tick()

    def stop_remote_watch(self) -> None:
        self.auto_online_var.set(False)
        if self.remote_watch_job is not None:
            self.root.after_cancel(self.remote_watch_job)
            self.remote_watch_job = None

    def ensure_serial_connection(self, action_name: str) -> RemoteSession | None:
        if self.remote is not None:
            return self.remote
        should_connect = messagebox.askyesno(
            "Serial connection required",
            f"{action_name} requires a serial connection to the board. Connect now?",
            parent=self.root,
        )
        if not should_connect:
            return None
        self.connect_serial()
        return self.remote

    def update_help_visibility(self) -> None:
        if self.help_text is None:
            return
        if self.help_var.get():
            self.help_text.grid()
        else:
            self.help_text.grid_remove()
            self.hide_tooltip()

    def render_help_text(self) -> None:
        if self.help_text is None:
            return
        tips = [
            ("[i]", " insert before"),
            ("[a]", " append after"),
            ("[b]", " branch under / stack lane"),
            ("[r]", " new rung after"),
            ("[Shift+R]", " new rung before"),
            ("[c]", " edit comment"),
            ("[f]", " force / unforce selected tag"),
            ("[x]", " delete rung or instruction"),
            ("[Enter]", " edit instruction"),
            ("[Left/Right]", " move in level / enter branch / leave top branch lane"),
            ("[Up/Down]", " move between branch levels"),
            ("[Shift+Up/Down]", " select previous / next rung"),
            ("[Shift+Left]", " select rung number"),
            ("[Shift+Right]", " select first instruction in rung"),
        ]
        self.help_text.configure(state="normal")
        self.help_text.delete("1.0", "end")
        self.help_text.tag_configure("key", font=("TkDefaultFont", 10, "bold"))
        self.help_text.tag_configure("green", foreground=PALETTE["success"])
        self.help_text.tag_configure("red", foreground=PALETTE["danger"])
        self.help_text.tag_configure("muted", foreground=PALETTE["muted"])
        for index, (key_text, desc) in enumerate(tips):
            color_tag = "green" if index % 2 == 0 else "red"
            self.help_text.insert("end", key_text, ("key", color_tag))
            self.help_text.insert("end", desc + "   ", (color_tag,))
        self.help_text.configure(state="disabled")

    def update_font_size(self) -> None:
        size = max(12, min(30, int(self.font_size_var.get())))
        self.font_size_var.set(size)
        self.fixed_font.configure(size=size)
        self.ladder_text.configure(font=self.fixed_font)
        self.render_ladder()

    def update_simulation_buttons(self) -> None:
        if self.step_button is not None:
            self.step_button.configure(style="ActionOn.TButton" if self.simulation_state == "stepped" else "ActionOff.TButton")
        if self.run_button is not None:
            self.run_button.configure(style="ActionOn.TButton" if self.simulation_state == "running" else "ActionOff.TButton")

    def register_tooltip(self, widget: tk.Misc, text: str) -> None:
        self.tooltip_text_by_widget[str(widget)] = text
        widget.bind("<Enter>", self.on_tooltip_enter, add="+")
        widget.bind("<Leave>", self.on_tooltip_leave, add="+")
        widget.bind("<Motion>", self.on_tooltip_motion, add="+")
        widget.bind("<ButtonPress>", self.on_tooltip_leave, add="+")
        widget.bind("<Destroy>", self.on_tooltip_leave, add="+")

    def on_tooltip_enter(self, event: tk.Event[tk.Misc]) -> None:
        self.tooltip_widget = event.widget
        self.cancel_tooltip()
        self.hide_tooltip()
        if not self.help_var.get():
            return
        self.tooltip_job = self.root.after(350, lambda: self.show_tooltip(event.widget, event.x_root, event.y_root))

    def on_tooltip_motion(self, event: tk.Event[tk.Misc]) -> None:
        if self.tooltip_window is not None and self.tooltip_widget == event.widget:
            self.position_tooltip(event.x_root, event.y_root)

    def on_tooltip_leave(self, event: tk.Event[tk.Misc] | None = None) -> None:
        self.cancel_tooltip()
        if event is None or event.widget == self.tooltip_widget:
            self.hide_tooltip()

    def cancel_tooltip(self) -> None:
        if self.tooltip_job is not None:
            self.root.after_cancel(self.tooltip_job)
            self.tooltip_job = None

    def show_tooltip(self, widget: tk.Misc, x_root: int, y_root: int) -> None:
        self.tooltip_job = None
        if not self.help_var.get():
            return
        text = self.tooltip_text_by_widget.get(str(widget))
        if not text:
            return
        if self.tooltip_window is None:
            self.tooltip_window = tk.Toplevel(self.root)
            self.tooltip_window.withdraw()
            self.tooltip_window.overrideredirect(True)
            self.tooltip_window.attributes("-topmost", True)
            self.tooltip_window.configure(bg=PALETTE["border"])
            self.tooltip_label = tk.Label(
                self.tooltip_window,
                text=text,
                bg=PALETTE["panel"],
                fg=PALETTE["text"],
                relief="flat",
                bd=0,
                justify="left",
                padx=10,
                pady=6,
                font=("TkDefaultFont", 10),
            )
            self.tooltip_label.pack()
        elif self.tooltip_label is not None:
            self.tooltip_label.configure(text=text)
        self.position_tooltip(x_root, y_root)
        self.tooltip_window.deiconify()

    def position_tooltip(self, x_root: int, y_root: int) -> None:
        if self.tooltip_window is None:
            return
        self.tooltip_window.geometry(f"+{x_root + 18}+{y_root + 14}")

    def hide_tooltip(self) -> None:
        if self.tooltip_window is not None:
            self.tooltip_window.withdraw()
        self.tooltip_widget = None

    def _selection_tag_name(self, key: str) -> str:
        return "select_" + key.replace(":", "_").replace(".", "_")

    def render_ladder(self) -> None:
        timer_values: dict[str, dict[str, object]] | None = None
        counter_values: dict[str, dict[str, object]] | None = None
        forced_tags: set[str] = set()
        show_timer_acc = self.mode_var.get() == "online" or self.simulation_state in {"running", "stepped"}
        if self.mode_var.get() == "online":
            tags = self.remote_snapshot.get("tags", {}) if isinstance(self.remote_snapshot, dict) else {}
            forced = self.remote_snapshot.get("forced", {}) if isinstance(self.remote_snapshot, dict) else {}
            forced_tags = set(forced.keys()) if isinstance(forced, dict) else set()
            timer_values = self.remote_snapshot.get("timers", {}) if isinstance(self.remote_snapshot, dict) else {}
            counter_values = self.remote_snapshot.get("counters", {}) if isinstance(self.remote_snapshot, dict) else {}
            rung_power, traces = trace_program_state(
                self.program,
                tags if isinstance(tags, dict) else {},
                forced if isinstance(forced, dict) else {},
            )
            _ = rung_power
        else:
            forced_tags = set(self.engine.forced.keys())
            if self.last_scan is not None:
                traces = self.last_scan.traces
                timer_values = self.last_scan.timers
                counter_values = self.last_scan.counters
            else:
                timer_values = {name: timer.snapshot() for name, timer in self.engine.timers.items()}
                counter_values = {name: counter.snapshot() for name, counter in self.engine.counters.items()}
                _, traces = trace_program_preview(
                    self.program,
                    self.engine.tags,
                    self.engine.forced,
                    timer_values=timer_values,
                    counter_values=counter_values,
                )

        document = LadderRenderer(
            self.program,
            traces=traces,
            timer_values=timer_values,
            counter_values=counter_values,
            forced_tags=forced_tags,
            show_timer_acc=show_timer_acc,
        ).render()
        self.current_document = document
        if self.selected_key not in document.selections:
            self.selected_key = None
        if self.selected_key is None and document.selections:
            self.selected_key = next(iter(document.selections.keys()))

        self.selection_tag_to_key.clear()
        self.ladder_text.configure(state="normal")
        self.ladder_text.delete("1.0", "end")
        self.ladder_text.insert("1.0", "\n".join(document.lines))
        for role, color in ROLE_TO_COLOR.items():
            self.ladder_text.tag_configure(role, foreground=color)
        self.ladder_text.tag_configure("selected", background="#38414c")

        for span in document.role_spans:
            start = f"{span.line + 1}.{span.start}"
            end = f"{span.line + 1}.{span.end}"
            self.ladder_text.tag_add(span.tag, start, end)

        for span in document.selection_spans:
            tag_name = self._selection_tag_name(span.tag)
            self.selection_tag_to_key[tag_name] = span.tag
            start = f"{span.line + 1}.{span.start}"
            end = f"{span.line + 1}.{span.end}"
            self.ladder_text.tag_add(tag_name, start, end)

        self.ladder_text.tag_remove("selected", "1.0", "end")
        if self.selected_key is not None:
            selected_tag = self._selection_tag_name(self.selected_key)
            self.ladder_text.tag_configure(selected_tag, underline=False)
            ranges = self.ladder_text.tag_ranges(selected_tag)
            for index in range(0, len(ranges), 2):
                self.ladder_text.tag_add("selected", ranges[index], ranges[index + 1])

        self.ladder_text.configure(state="disabled")
        self.root.title(f"PLC ASCII IDE - {self.program.name} - {'online' if self.mode_var.get() == 'online' else 'offline'}")
        self.ladder_text.focus_set()
        self.render_monitor()

    def on_click(self, event: tk.Event[tk.Text]) -> str:
        if self.is_live_locked():
            return "break"
        self.ladder_text.focus_set()
        index = self.ladder_text.index(f"@{event.x},{event.y}")
        for tag_name in reversed(self.ladder_text.tag_names(index)):
            if tag_name in self.selection_tag_to_key:
                self.selected_key = self.selection_tag_to_key[tag_name]
                self.render_ladder()
                return "break"
        return "break"

    def on_double_click(self, event: tk.Event[tk.Text]) -> str:
        if self.is_live_locked():
            return "break"
        self.on_click(event)
        self.edit_selected()
        return "break"

    def on_key_press(self, event: tk.Event[tk.Text]) -> str:
        if self.is_live_locked():
            return "break"
        key = event.keysym.lower()
        char = event.char.lower() if event.char else ""
        shifted = bool(event.state & 0x1)
        if key == "left":
            if shifted:
                self.select_current_rung()
            else:
                self.move_selection_horizontal(-1)
        elif key == "right":
            if shifted:
                self.select_first_instruction()
            else:
                self.move_selection_horizontal(1)
        elif key == "up":
            if shifted:
                self.move_rung_selection(-1)
            else:
                self.move_branch_level(-1)
        elif key == "down":
            if shifted:
                self.move_rung_selection(1)
            else:
                self.move_branch_level(1)
        elif char == "i":
            self.insert_instruction(before=True)
        elif char == "a":
            self.insert_instruction(before=False)
        elif char == "r" and shifted:
            self.insert_rung_before()
        elif char == "r":
            self.add_rung_after()
        elif char == "u":
            self.move_rung(-1)
        elif char == "d":
            self.move_rung(1)
        elif char == "b":
            self.create_branch_under()
        elif char == "c":
            self.edit_rung_comment()
        elif char == "f":
            self.toggle_force_selected()
        elif char == "x":
            self.delete_selected()
        elif key in {"return", "kp_enter"}:
            self.edit_selected()
        elif key in {"delete", "backspace"}:
            self.delete_selected()
        return "break"

    def resolve_container_by_prefix(self, rung_index: int, parent_path: tuple[int, ...]) -> list[Node]:
        nodes = self.program.rungs[rung_index].elements
        current_nodes = nodes
        cursor = 0
        while cursor < len(parent_path):
            node_index = parent_path[cursor]
            lane_index = parent_path[cursor + 1]
            branch = current_nodes[node_index]
            if not isinstance(branch, Branch):
                raise ValueError("Invalid container path")
            current_nodes = branch.lanes[lane_index]
            cursor += 2
        return current_nodes

    def edge_step_path_in_node(self, node: Node, node_path: tuple[int, ...], direction: int) -> tuple[int, ...] | None:
        if isinstance(node, Step):
            return node_path
        if not node.lanes:
            return None
        return self.edge_step_path_in_sequence(node.lanes[0], node_path + (0,), direction)

    def edge_step_path_in_sequence(
        self,
        nodes: list[Node],
        path_prefix: tuple[int, ...],
        direction: int,
    ) -> tuple[int, ...] | None:
        if not nodes:
            return None
        indices = range(len(nodes)) if direction >= 0 else range(len(nodes) - 1, -1, -1)
        for index in indices:
            path = self.edge_step_path_in_node(nodes[index], path_prefix + (index,), direction)
            if path is not None:
                return path
        return None

    def move_selection_horizontal(self, delta: int) -> None:
        selection = self.current_selection()
        if selection is None:
            return
        if selection.kind != "step" or selection.path is None:
            return
        parent_path = selection.path[:-1]
        container = self.resolve_container_by_prefix(selection.rung_index, parent_path)
        current_index = selection.path[-1]
        target_index = current_index + delta

        if 0 <= target_index < len(container):
            target_path = self.edge_step_path_in_node(
                container[target_index],
                parent_path + (target_index,),
                delta,
            )
            if target_path is None:
                return
            self.selected_key = step_selection_key(selection.rung_index, target_path)
            self.render_ladder()
            return

        if len(parent_path) >= 2 and parent_path[-1] == 0:
            outer_parent_path = parent_path[:-2]
            branch_index = parent_path[-2]
            outer_container = self.resolve_container_by_prefix(selection.rung_index, outer_parent_path)
            outer_target_index = branch_index + delta
            if 0 <= outer_target_index < len(outer_container):
                target_path = self.edge_step_path_in_node(
                    outer_container[outer_target_index],
                    outer_parent_path + (outer_target_index,),
                    delta,
                )
                if target_path is None:
                    return
                self.selected_key = step_selection_key(selection.rung_index, target_path)
                self.render_ladder()

    def select_current_rung(self) -> None:
        self.selected_key = f"rung:{self.current_rung_index()}"
        self.render_ladder()

    def select_first_instruction(self) -> None:
        rung_index = self.current_rung_index()
        if rung_index >= len(self.program.rungs):
            return
        path = first_step_path(self.program.rungs[rung_index].elements)
        if path is None:
            return
        self.selected_key = step_selection_key(rung_index, path)
        self.render_ladder()

    def move_rung_selection(self, delta: int) -> None:
        rung_index = self.current_rung_index()
        target = max(0, min(len(self.program.rungs) - 1, rung_index + delta))
        self.selected_key = f"rung:{target}"
        self.render_ladder()

    def move_branch_level(self, delta: int) -> None:
        selection = self.current_selection()
        if selection is None or selection.path is None:
            return
        rung = self.program.rungs[selection.rung_index]
        if selection.kind == "step":
            if len(selection.path) < 3:
                return
            branch_path = selection.path[:-2]
            lane_index = selection.path[-2]
            preferred_index = selection.path[-1]
        elif selection.kind in {"branch_start", "branch_end"}:
            branch_path = selection.path
            lane_index = 0
            preferred_index = 0
        else:
            return

        branch = get_node_at_path(rung.elements, branch_path)
        if not isinstance(branch, Branch):
            return
        target_lane = lane_index + delta
        if target_lane < 0 or target_lane >= len(branch.lanes):
            return
        lane = branch.lanes[target_lane]
        if not lane:
            return
        target_index = min(preferred_index, len(lane) - 1)
        target_path = self.edge_step_path_in_node(
            lane[target_index],
            branch_path + (target_lane, target_index),
            1,
        )
        if target_path is None:
            target_path = self.edge_step_path_in_sequence(lane, branch_path + (target_lane,), 1)
        if target_path is None:
            return
        self.selected_key = step_selection_key(selection.rung_index, target_path)
        self.render_ladder()

    def new_program(self) -> None:
        self.stop_run()
        self.program = Program(name="untitled", rungs=[Rung(comment="", elements=[])])
        self.program_path = None
        self.engine = LadderEngine(self.program)
        self.sync_program_variables(save_current_values=False)
        self.last_scan = None
        self.simulation_state = "stopped"
        self.update_simulation_buttons()
        self.selected_key = None
        self.status_var.set("Created new program")
        self.render_ladder()

    def open_program(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="Open ladder program",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        try:
            self.stop_run()
            self.program = load_program(path)
            self.program_path = Path(path)
            self.engine = LadderEngine(self.program)
            self.sync_program_variables(save_current_values=False)
            self.last_scan = None
            self.simulation_state = "stopped"
            self.update_simulation_buttons()
            self.selected_key = None
        except Exception as exc:
            messagebox.showerror("Open failed", str(exc), parent=self.root)
            return
        self.status_var.set(f"Loaded {path}")
        self.render_ladder()

    def save_program(self) -> None:
        if self.program_path is None:
            self.save_program_as()
            return
        try:
            self.sync_program_variables(save_current_values=True)
            save_program(self.program, self.program_path)
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc), parent=self.root)
            return
        self.status_var.set(f"Saved {self.program_path}")

    def save_program_as(self) -> None:
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save ladder program",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")],
        )
        if not path:
            return
        self.program_path = Path(path)
        self.save_program()

    def manage_bindings(self) -> None:
        if not self.ensure_live_editable():
            return
        BindingsManagerDialog(self.root, self.program)
        self.render_ladder()

    def edit_rung_comment(self) -> None:
        if not self.ensure_live_editable():
            return
        rung_index = self.current_rung_index()
        rung = self.program.rungs[rung_index]
        comment = simpledialog.askstring("Rung comment", "Comment", parent=self.root, initialvalue=rung.comment)
        if comment is None:
            return
        rung.comment = comment
        self.status_var.set(f"Updated comment for rung {rung_index + 1:03d}")
        self.render_ladder()

    def insert_instruction(self, before: bool) -> None:
        if not self.ensure_live_editable():
            return
        selection = self.current_selection()
        dialog = StepDialog(self.root, title="Insert instruction")
        if dialog.result is None:
            return
        try:
            self.validate_step_type_compatibility(dialog.result)
        except Exception as exc:
            messagebox.showerror("Invalid instruction", str(exc), parent=self.root)
            return

        rung_index = self.current_rung_index()
        rung = self.program.rungs[rung_index]
        if selection is None or selection.kind == "rung":
            rung.elements.append(dialog.result)
            new_index = len(rung.elements) - 1
            self.selected_key = step_selection_key(rung_index, (new_index,))
        elif selection.kind == "step" and selection.path is not None:
            container, index = resolve_parent_list(rung.elements, selection.path)
            container.insert(index if before else index + 1, dialog.result)
            new_path = selection.path[:-1] + ((selection.path[-1] if before else selection.path[-1] + 1),)
            self.selected_key = step_selection_key(selection.rung_index, new_path)
        elif selection.kind == "branch_start" and selection.path is not None:
            container, index = resolve_parent_list(rung.elements, selection.path)
            container.insert(index, dialog.result)
            self.selected_key = step_selection_key(selection.rung_index, (*selection.path[:-1], index))
        elif selection.kind == "branch_end" and selection.path is not None:
            container, index = resolve_parent_list(rung.elements, selection.path)
            container.insert(index + 1, dialog.result)
            self.selected_key = step_selection_key(selection.rung_index, (*selection.path[:-1], index + 1))
        self.sync_program_variables(save_current_values=True)
        self.last_scan = None
        self.status_var.set("Inserted instruction")
        self.render_ladder()

    def add_rung_after(self) -> None:
        if not self.ensure_live_editable():
            return
        if not self.program.rungs:
            self.program.rungs.append(Rung(comment="", elements=[]))
            self.engine.load_program(self.program)
            self.last_scan = None
            self.selected_key = "rung:0"
            self.status_var.set("Added rung 001")
            self.render_ladder()
            return
        rung_index = self.current_rung_index()
        self.program.rungs.insert(rung_index + 1, Rung(comment="", elements=[]))
        self.engine.load_program(self.program)
        self.last_scan = None
        self.selected_key = f"rung:{rung_index + 1}"
        self.status_var.set(f"Added rung {rung_index + 2:03d}")
        self.render_ladder()

    def insert_rung_before(self) -> None:
        if not self.ensure_live_editable():
            return
        if not self.program.rungs:
            self.program.rungs.append(Rung(comment="", elements=[]))
            self.engine.load_program(self.program)
            self.last_scan = None
            self.selected_key = "rung:0"
            self.status_var.set("Inserted rung 001")
            self.render_ladder()
            return
        rung_index = self.current_rung_index()
        self.program.rungs.insert(rung_index, Rung(comment="", elements=[]))
        self.engine.load_program(self.program)
        self.last_scan = None
        self.selected_key = f"rung:{rung_index}"
        self.status_var.set(f"Inserted rung {rung_index + 1:03d}")
        self.render_ladder()

    def move_rung(self, direction: int) -> None:
        if not self.ensure_live_editable():
            return
        rung_index = self.current_rung_index()
        target = rung_index + direction
        if target < 0 or target >= len(self.program.rungs):
            return
        self.program.rungs[rung_index], self.program.rungs[target] = self.program.rungs[target], self.program.rungs[rung_index]
        self.engine.load_program(self.program)
        self.last_scan = None
        self.selected_key = f"rung:{target}"
        self.status_var.set(f"Moved rung to {target + 1:03d}")
        self.render_ladder()

    def create_branch_under(self) -> None:
        if not self.ensure_live_editable():
            return
        selection = self.current_selection()
        if selection is None or selection.kind != "step" or selection.path is None:
            return
        rung = self.program.rungs[selection.rung_index]
        dialog = StepDialog(self.root, title="New branch instruction")
        if dialog.result is not None:
            try:
                self.validate_step_type_compatibility(dialog.result)
            except Exception as exc:
                messagebox.showerror("Invalid instruction", str(exc), parent=self.root)
                return

        if len(selection.path) >= 3:
            parent_branch_path = selection.path[:-2]
            lane_index = selection.path[-2]
            parent_branch = get_node_at_path(rung.elements, parent_branch_path)
            if isinstance(parent_branch, Branch):
                new_lane: list[Node] = []
                insert_index = min(lane_index + 1, len(parent_branch.lanes))
                parent_branch.lanes.insert(insert_index, new_lane)
                if dialog.result is not None:
                    new_lane.append(dialog.result)
                    new_path = (*parent_branch_path, insert_index, 0)
                    self.selected_key = f"step:{selection.rung_index}:{'.'.join(str(part) for part in new_path)}"
                else:
                    self.selected_key = f"branch_end:{selection.rung_index}:{'.'.join(str(part) for part in parent_branch_path)}"
                self.sync_program_variables(save_current_values=True)
                self.last_scan = None
                self.status_var.set("Stacked branch lane")
                self.render_ladder()
                return

        container, index = resolve_parent_list(rung.elements, selection.path)
        selected_node = container[index]
        new_branch = Branch(lanes=[[selected_node], []])
        container[index] = new_branch

        if dialog.result is not None:
            new_branch.lanes[1].append(dialog.result)
            self.selected_key = f"step:{selection.rung_index}:{'.'.join(str(part) for part in (*selection.path, 1, 0))}"
        else:
            self.selected_key = f"branch_end:{selection.rung_index}:{'.'.join(str(part) for part in selection.path)}"

        self.sync_program_variables(save_current_values=True)
        self.last_scan = None
        self.status_var.set("Created branch")
        self.render_ladder()

    def edit_selected(self) -> None:
        if not self.ensure_live_editable():
            return
        selection = self.current_selection()
        if selection is None:
            return
        if selection.kind == "rung":
            self.edit_rung_comment()
            return
        if selection.kind != "step" or selection.path is None:
            return
        rung = self.program.rungs[selection.rung_index]
        container, index = resolve_parent_list(rung.elements, selection.path)
        current = container[index]
        if not isinstance(current, Step):
            return
        dialog = StepDialog(self.root, title="Edit instruction", initial=current)
        if dialog.result is None:
            return
        try:
            self.validate_step_type_compatibility(dialog.result)
        except Exception as exc:
            messagebox.showerror("Invalid instruction", str(exc), parent=self.root)
            return
        container[index] = dialog.result
        self.sync_program_variables(save_current_values=True)
        self.last_scan = None
        self.status_var.set("Updated instruction")
        self.render_ladder()

    def delete_selected(self) -> None:
        if not self.ensure_live_editable():
            return
        selection = self.current_selection()
        if selection is None:
            return
        if selection.kind == "rung":
            if not self.program.rungs:
                return
            self.program.rungs.pop(selection.rung_index)
            if not self.program.rungs:
                self.program.rungs.append(Rung(comment="", elements=[]))
            self.sync_program_variables(save_current_values=True)
            self.last_scan = None
            self.selected_key = f"rung:{min(selection.rung_index, len(self.program.rungs) - 1)}"
            self.status_var.set("Deleted rung")
            self.render_ladder()
            return
        if selection.kind == "step" and selection.path is not None:
            rung = self.program.rungs[selection.rung_index]
            container, index = resolve_parent_list(rung.elements, selection.path)
            container.pop(index)
            rung.elements = normalize_nodes(rung.elements)
            self.sync_program_variables(save_current_values=True)
            self.last_scan = None
            self.selected_key = f"rung:{selection.rung_index}"
            self.status_var.set("Deleted instruction")
            self.render_ladder()

    def _offline_scan(self, *, state_after_scan: str) -> bool:
        if self.mode_var.get() != "offline":
            return False
        scan_ms = max(10, int(self.scan_ms_var.get()))
        self.last_scan = self.engine.scan(scan_ms=scan_ms)
        self.simulation_state = state_after_scan
        self.update_simulation_buttons()
        self.status_var.set(
            f"Executed one offline scan ({scan_ms} ms)"
            if state_after_scan == "stepped"
            else f"Running offline simulation ({scan_ms} ms scan)"
        )
        self.render_ladder()
        return True

    def step_scan(self) -> None:
        if self.mode_var.get() != "offline":
            self.status_var.set("Step is only available in offline mode")
            return
        self._offline_scan(state_after_scan="stepped")

    def _run_tick(self) -> None:
        if self.mode_var.get() != "offline":
            self.stop_run()
            return
        self._offline_scan(state_after_scan="running")
        self.run_job = self.root.after(max(10, int(self.scan_ms_var.get())), self._run_tick)

    def start_run(self) -> None:
        if self.mode_var.get() != "offline":
            self.status_var.set("Run is only available in offline mode")
            return
        if self.run_job is None:
            self.simulation_state = "running"
            self.update_simulation_buttons()
            self.run_job = self.root.after(0, self._run_tick)
            self.status_var.set("Started offline simulation")

    def stop_run(self) -> None:
        if self.mode_var.get() != "offline":
            self.status_var.set("Stop is only available in offline mode")
            return
        was_active = self.run_job is not None or self.simulation_state == "stepped"
        if self.run_job is not None:
            self.root.after_cancel(self.run_job)
            self.run_job = None
        self.last_scan = None
        self.simulation_state = "stopped"
        self.update_simulation_buttons()
        if was_active:
            self.engine.stop_offline(reset_numeric=self.reset_integer_var.get(), clear_forces=False)
            self.status_var.set("Stopped offline simulation")
        else:
            self.engine.stop_offline(reset_numeric=self.reset_integer_var.get(), clear_forces=True)
            self.status_var.set("Cleared forces and stopped offline simulation")
        self.render_ladder()

    def prompt_serial_target(self) -> tuple[str, int] | None:
        port = simpledialog.askstring("Serial port", "Port", parent=self.root, initialvalue=self.last_serial_port)
        if not port:
            return None
        baud = simpledialog.askinteger("Serial baud", "Baud", parent=self.root, initialvalue=self.last_serial_baud)
        if baud is None:
            return None
        self.last_serial_port = port
        self.last_serial_baud = baud
        return port, baud

    def connect_serial(self) -> None:
        target = self.prompt_serial_target()
        if target is None:
            return
        port, baud = target
        self.disconnect_remote(silent=True)
        try:
            session = RemoteSession(SerialJsonTransport(port=port, baudrate=baud))
            hello = session.hello(timeout=1.0)
            if not hello and isinstance(session.transport, SerialJsonTransport):
                session.transport.soft_reboot()
                hello = session.hello(timeout=2.0)
        except Exception as exc:
            messagebox.showerror("Serial connection failed", str(exc), parent=self.root)
            return
        if not hello:
            messagebox.showerror("Serial connection failed", "No response from target.", parent=self.root)
            return
        self.remote = session
        self.remote_label = f"serial:{port}"
        try:
            self.remote.set_mode("run", timeout=0.5)
        except Exception:
            pass
        self.status_var.set(f"Connected to {port}")
        self.mode_var.set("offline")
        self.update_connection_indicator()

    def install_circuitpython_runtime(self) -> None:
        target = self.prompt_serial_target()
        if target is None:
            return
        port, _baud = target
        try:
            self.sync_program_variables(save_current_values=True)
            install_circuitpython_runtime(port, program=self.program)
        except Exception as exc:
            messagebox.showerror("Install failed", str(exc), parent=self.root)
            return
        self.status_var.set(f"Installed CircuitPython runtime on {port}")
        messagebox.showinfo(
            "Runtime installed",
            f"Installed the CircuitPython runtime on {port}.\nUse Go Online, Download, or Upload to connect and work with the board.",
            parent=self.root,
        )

    def disconnect_remote(self, silent: bool = False) -> None:
        if self.remote is not None:
            try:
                self.remote.transport.close()
            except Exception:
                pass
        self.remote = None
        self.remote_label = None
        self.remote_snapshot = {}
        self.stop_remote_watch()
        self.mode_var.set("offline")
        self.update_connection_indicator()
        if not silent:
            self.status_var.set("Disconnected from board")
        self.render_ladder()

    def require_remote(self) -> RemoteSession | None:
        if self.remote is None:
            messagebox.showinfo("Board connection", "Connect to the board first.", parent=self.root)
            return None
        return self.remote

    def remote_snapshot_request(self) -> None:
        remote = self.require_remote()
        if remote is None:
            return
        try:
            response = remote.request_snapshot(timeout=0.5)
        except Exception as exc:
            messagebox.showerror("Snapshot failed", str(exc), parent=self.root)
            return
        if response is None:
            self.status_var.set("Remote snapshot timed out")
            return
        self.remote_snapshot = response
        self.mode_var.set("online")
        self.status_var.set("Updated online snapshot")
        self.update_connection_indicator()
        self.render_ladder()

    def remote_download_program(self) -> None:
        remote = self.ensure_serial_connection("Download")
        if remote is None:
            return
        was_watching = self.auto_online_var.get()
        self.stop_remote_watch()
        response = None
        try:
            self.sync_program_variables(save_current_values=True)
            response = remote.download_program(self.program, timeout=1.0)
            try:
                remote.set_mode("run", timeout=0.5)
            except Exception:
                pass
        except Exception as exc:
            messagebox.showerror("Download failed", str(exc), parent=self.root)
        else:
            if response is None:
                self.status_var.set("Remote download timed out")
            else:
                self.status_var.set("Downloaded program to board runtime")
                self.update_connection_indicator()
        finally:
            if was_watching and self.mode_var.get() == "online":
                self.start_remote_watch()
                if response is not None:
                    self.remote_snapshot_request()

    def remote_upload_program(self) -> None:
        remote = self.ensure_serial_connection("Upload")
        if remote is None:
            return
        was_watching = self.auto_online_var.get()
        self.stop_remote_watch()
        response = None
        try:
            response = remote.upload_program(timeout=1.0)
        except Exception as exc:
            messagebox.showerror("Upload failed", str(exc), parent=self.root)
        else:
            if response is None:
                self.status_var.set("Remote upload timed out")
            elif response.get("type") != "program" or "program" not in response:
                messagebox.showerror("Upload failed", f"Unexpected response: {response}", parent=self.root)
            else:
                try:
                    self.program = Program.from_dict(response["program"])
                    self.engine.load_program(self.program)
                    self.sync_program_variables(save_current_values=False)
                except Exception as exc:
                    messagebox.showerror("Upload failed", str(exc), parent=self.root)
                else:
                    self.last_scan = None
                    self.status_var.set("Uploaded program from board runtime")
                    self.update_connection_indicator()
        finally:
            if was_watching and self.mode_var.get() == "online":
                self.start_remote_watch()
                if response is not None and response.get("type") == "program":
                    self.remote_snapshot_request()

    def go_online(self) -> None:
        remote = self.ensure_serial_connection("Go Online")
        if remote is None:
            return
        try:
            remote.set_mode("run", timeout=0.5)
        except Exception:
            pass
        self.mode_var.set("online")
        self.update_connection_indicator()
        self.status_var.set("Online live view active")
        self.start_remote_watch()
        self.remote_snapshot_request()

    def _remote_watch_tick(self) -> None:
        if not self.auto_online_var.get():
            self.remote_watch_job = None
            return
        if self.remote is not None:
            try:
                response = self.remote.request_snapshot(timeout=0.3)
                if response is not None:
                    self.remote_snapshot = response
                    self.render_ladder()
            except Exception:
                self.auto_online_var.set(False)
                self.remote_watch_job = None
                self.status_var.set("Lost communication with board runtime")
                self.mode_var.set("offline")
                self.update_connection_indicator()
                return
        self.remote_watch_job = self.root.after(500, self._remote_watch_tick)

    def set_tag_dialog(self) -> None:
        if not self.ensure_live_editable():
            return
        default_tag = default_tag_for_selection(self.current_selection(), self.program)
        tag = simpledialog.askstring("Set tag", "Tag", parent=self.root, initialvalue=default_tag or "")
        if not tag:
            return
        current_value = self.engine.read_tag(tag) if self.mode_var.get() == "offline" else False
        value = ask_runtime_value(self.root, "Set tag", f"Value for {tag}", initial=format_runtime_value(current_value))
        if value is None:
            return
        if self.mode_var.get() == "online":
            remote = self.require_remote()
            if remote is None:
                return
            remote.set_tag(tag, value, timeout=0.5)
            self.remote_snapshot_request()
        else:
            self.engine.set_tag(tag, value)
            self.last_scan = None
            self.status_var.set(f"Set {tag} = {format_runtime_value(value)}")
            self.render_ladder()

    def force_tag_dialog(self) -> None:
        if not self.ensure_live_editable():
            return
        default_tag = default_tag_for_selection(self.current_selection(), self.program)
        tag = simpledialog.askstring("Force tag", "Tag", parent=self.root, initialvalue=default_tag or "")
        if not tag:
            return
        current_value = self.engine.read_tag(tag) if self.mode_var.get() == "offline" else False
        value = ask_runtime_value(self.root, "Force tag", f"Force value for {tag}", initial=format_runtime_value(current_value))
        if value is None:
            return
        if self.mode_var.get() == "online":
            remote = self.require_remote()
            if remote is None:
                return
            remote.force_tag(tag, enabled=True, value=value, timeout=0.5)
            self.remote_snapshot_request()
        else:
            self.engine.set_force(tag, value)
            self.last_scan = None
            self.status_var.set(f"Forced {tag} = {format_runtime_value(value)}")
            self.render_ladder()

    def unforce_tag_dialog(self) -> None:
        if not self.ensure_live_editable():
            return
        default_tag = default_tag_for_selection(self.current_selection(), self.program)
        tag = simpledialog.askstring("Unforce tag", "Tag", parent=self.root, initialvalue=default_tag or "")
        if not tag:
            return
        if self.mode_var.get() == "online":
            remote = self.require_remote()
            if remote is None:
                return
            remote.force_tag(tag, enabled=False, value=False, timeout=0.5)
            self.remote_snapshot_request()
        else:
            self.engine.clear_force(tag)
            self.last_scan = None
            self.status_var.set(f"Removed force from {tag}")
            self.render_ladder()

    def toggle_force_selected(self) -> None:
        if not self.ensure_live_editable():
            return
        tag = default_tag_for_selection(self.current_selection(), self.program)
        if not tag:
            return

        if self.mode_var.get() == "online":
            forced = self.remote_snapshot.get("forced", {}) if isinstance(self.remote_snapshot, dict) else {}
            if tag in forced:
                remote = self.require_remote()
                if remote is None:
                    return
                remote.force_tag(tag, enabled=False, value=False, timeout=0.5)
                self.remote_snapshot_request()
                self.status_var.set(f"Removed force from {tag}")
                return
            tags = self.remote_snapshot.get("tags", {}) if isinstance(self.remote_snapshot, dict) else {}
            current_value = tags.get(tag, False) if isinstance(tags, dict) else False
            value = ask_runtime_value(self.root, "Force tag", f"Force value for {tag}", initial=format_runtime_value(current_value))
            if value is None:
                return
            remote = self.require_remote()
            if remote is None:
                return
            remote.force_tag(tag, enabled=True, value=value, timeout=0.5)
            self.remote_snapshot_request()
            self.status_var.set(f"Forced {tag} = {format_runtime_value(value)}")
            return

        if tag in self.engine.forced:
            self.engine.clear_force(tag)
            self.last_scan = None
            self.status_var.set(f"Removed force from {tag}")
            self.render_ladder()
            return

        current_value = self.engine.read_tag(tag)
        value = ask_runtime_value(self.root, "Force tag", f"Force value for {tag}", initial=format_runtime_value(current_value))
        if value is None:
            return
        self.engine.set_force(tag, value)
        self.last_scan = None
        self.status_var.set(f"Forced {tag} = {format_runtime_value(value)}")
        self.render_ladder()

    def on_close(self) -> None:
        self.stop_run()
        self.disconnect_remote(silent=True)
        self.root.destroy()

    def run(self) -> None:
        self.render_ladder()
        self.root.mainloop()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PLC ASCII Tkinter IDE")
    parser.add_argument("program", nargs="?", help="Optional JSON ladder program to load")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    path = Path(args.program) if args.program else None
    program = load_program(path) if path else None
    PLCAsciiIDE(program=program, program_path=path).run()


if __name__ == "__main__":
    main()
