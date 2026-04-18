from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font, messagebox, simpledialog, ttk

from .engine import LadderEngine, ScanResult, trace_program_state
from .model import Binding, Branch, Node, Program, Rung, Step
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
from .subprocess_link import SubprocessJsonTransport


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


def parse_bool(raw: str) -> bool:
    value = raw.strip().lower()
    if value in {"1", "true", "on", "yes"}:
        return True
    if value in {"0", "false", "off", "no"}:
        return False
    raise ValueError(f"Cannot parse boolean from '{raw}'")


def ask_bool(parent: tk.Misc, title: str, prompt: str, initial: str = "0") -> bool | None:
    raw = simpledialog.askstring(title, prompt, parent=parent, initialvalue=initial)
    if raw is None:
        return None
    return parse_bool(raw)


def default_tag_for_selection(selection: SelectionTarget | None, program: Program) -> str | None:
    if selection is None or selection.kind != "step" or selection.path is None:
        return None
    node = get_node_at_path(program.rungs[selection.rung_index].elements, selection.path)
    if isinstance(node, Step):
        return node.tag
    return None


class StepDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, *, title: str, initial: Step | None = None) -> None:
        super().__init__(parent)
        self.title(title)
        self.transient(parent)
        self.configure(bg=PALETTE["panel"])
        self.resizable(False, False)
        self.result: Step | None = None

        self.op_var = tk.StringVar(value=initial.op if initial else "")
        self.tag_var = tk.StringVar(value=initial.tag if initial else "")
        self.arg_var = tk.StringVar(value=str(initial.arg) if initial and initial.arg is not None else "")
        self.filter_var = tk.StringVar(value=self.op_var.get())
        self.available_ops = ["XIC", "XIO", "OTE", "OTL", "OTU", "TON"]

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

        ttk.Label(body, text="Tag").grid(row=2, column=0, sticky="w", pady=(0, 8))
        self.tag_entry = ttk.Entry(body, textvariable=self.tag_var, width=28)
        self.tag_entry.grid(row=2, column=1, sticky="ew", pady=(0, 8))

        ttk.Label(body, text="Preset (ms)").grid(row=3, column=0, sticky="w")
        self.arg_entry = ttk.Entry(body, textvariable=self.arg_var, width=28)
        self.arg_entry.grid(row=3, column=1, sticky="ew")

        buttons = ttk.Frame(body, style="Card.TFrame")
        buttons.grid(row=4, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ttk.Button(buttons, text="Cancel", command=self.destroy, style="Tool.TButton").pack(side="right", padx=(8, 0))
        ttk.Button(buttons, text="OK", command=self.on_ok, style="Accent.TButton").pack(side="right")

        self.filter_var.trace_add("write", lambda *_: self._refresh_list())
        self.op_var.trace_add("write", lambda *_: self._update_preset_state())
        self._update_preset_state()
        self._refresh_list()

        self.bind("<Return>", lambda event: self.on_ok())
        self.bind("<Escape>", lambda event: self.destroy())
        self.grab_set()
        self.filter_entry.focus_set()
        self.wait_window(self)

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

    def _update_preset_state(self) -> None:
        if self.op_var.get() == "TON":
            self.arg_entry.state(["!disabled"])
        else:
            self.arg_entry.state(["disabled"])
            self.arg_var.set("")

    def on_ok(self) -> None:
        try:
            chosen_op = self.op_var.get().strip().upper() or self.filter_var.get().strip().upper()
            if chosen_op not in self.available_ops:
                raise ValueError("Choose an instruction type")
            arg = int(self.arg_var.get()) if chosen_op == "TON" else None
            step = Step(op=chosen_op, tag=self.tag_var.get().strip(), arg=arg)
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
        self.remote_snapshot: dict[str, object] = {}
        self.remote_watch_job: str | None = None
        self.run_job: str | None = None
        self.current_document: RenderedDocument | None = None
        self.selected_key: str | None = None
        self.selection_tag_to_key: dict[str, str] = {}
        self.help_text: tk.Text | None = None
        self.tooltip_text_by_widget: dict[str, str] = {}
        self.tooltip_job: str | None = None
        self.tooltip_window: tk.Toplevel | None = None
        self.tooltip_label: tk.Label | None = None
        self.tooltip_widget: tk.Misc | None = None

        self.mode_var = tk.StringVar(value="offline")
        self.status_var = tk.StringVar(value="Offline programming / simulation")
        self.auto_online_var = tk.BooleanVar(value=False)
        self.help_var = tk.BooleanVar(value=False)
        self.scan_ms_var = tk.IntVar(value=100)
        self.font_size_var = tk.IntVar(value=18)

        self.fixed_font = font.nametofont("TkFixedFont").copy()
        self.fixed_font.configure(size=self.font_size_var.get())

        self._apply_theme()
        self._build_menu()
        self._build_layout()
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
        style.configure("TEntry", fieldbackground=PALETTE["panel_alt"], foreground=PALETTE["text"], insertcolor=PALETTE["text"])
        style.configure("TCombobox", fieldbackground=PALETTE["panel_alt"], background=PALETTE["panel_alt"], foreground=PALETTE["text"], arrowcolor=PALETTE["text"])
        style.configure("TRadiobutton", background=PALETTE["bg"], foreground=PALETTE["text"])
        style.configure("TCheckbutton", background=PALETTE["bg"], foreground=PALETTE["text"])
        style.configure("TSpinbox", fieldbackground=PALETTE["panel_alt"], foreground=PALETTE["text"])

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

        debug_menu = tk.Menu(menu, tearoff=False, bg=PALETTE["panel"], fg=PALETTE["text"], activebackground=PALETTE["accent"], activeforeground=PALETTE["text"])
        debug_menu.add_command(label="Set Tag", command=self.set_tag_dialog)
        debug_menu.add_command(label="Force Tag", command=self.force_tag_dialog)
        debug_menu.add_command(label="Unforce Tag", command=self.unforce_tag_dialog)
        debug_menu.add_command(label="Edit Comment", command=self.edit_rung_comment)
        menu.add_cascade(label="Debug", menu=debug_menu)
        self.root.config(menu=menu)

    def _build_layout(self) -> None:
        outer = ttk.Frame(self.root, padding=(12, 10, 12, 12), style="Card.TFrame")
        outer.pack(fill="both", expand=True)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(outer, style="Card.TFrame")
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        for label, command, style_name, tooltip in [
            ("Step", self.step_scan, "Tool.TButton", "Execute one offline PLC scan."),
            ("Run", self.start_run, "Accent.TButton", "Start continuous offline simulation scans."),
            ("Stop", self.stop_run, "Tool.TButton", "Stop the offline simulation loop."),
            ("Connect Demo", self.connect_demo, "Accent.TButton", "Launch and connect to the bundled demo runtime."),
            ("Serial", self.connect_serial, "Tool.TButton", "Connect to a target over the serial JSON link."),
            ("Snapshot", self.remote_snapshot_request, "Tool.TButton", "Refresh the online snapshot from the connected target."),
        ]:
            button = ttk.Button(toolbar, text=label, command=command, style=style_name)
            button.pack(side="left", padx=(0, 8))
            self.register_tooltip(button, tooltip)

        mode_label = ttk.Label(toolbar, text="Mode", style="Subtle.TLabel")
        mode_label.pack(side="left", padx=(14, 6))
        self.register_tooltip(mode_label, "Choose between local offline work and live online monitoring.")

        offline_button = ttk.Radiobutton(toolbar, text="Offline", value="offline", variable=self.mode_var, command=self.on_mode_change)
        offline_button.pack(side="left")
        self.register_tooltip(offline_button, "Work on the local ladder program and simulation engine.")

        online_button = ttk.Radiobutton(toolbar, text="Online", value="online", variable=self.mode_var, command=self.on_mode_change)
        online_button.pack(side="left", padx=(0, 8))
        self.register_tooltip(online_button, "View and debug the live state from the connected runtime.")

        auto_button = ttk.Checkbutton(toolbar, text="Auto", variable=self.auto_online_var, command=self.toggle_remote_watch)
        auto_button.pack(side="left")
        self.register_tooltip(auto_button, "Continuously poll the connected target for fresh online data.")

        help_button = ttk.Checkbutton(toolbar, text="Help", variable=self.help_var, command=self.update_help_visibility)
        help_button.pack(side="left", padx=(12, 0))
        self.register_tooltip(help_button, "Show keyboard shortcuts below and enable hover tooltips.")

        scan_label = ttk.Label(toolbar, text="Scan", style="Subtle.TLabel")
        scan_label.pack(side="left", padx=(14, 6))
        self.register_tooltip(scan_label, "Offline scan period in milliseconds.")

        scan_spinbox = ttk.Spinbox(toolbar, from_=10, to=5000, increment=10, textvariable=self.scan_ms_var, width=7)
        scan_spinbox.pack(side="left")
        self.register_tooltip(scan_spinbox, "Set the offline scan time in milliseconds.")

        font_label = ttk.Label(toolbar, text="Font", style="Subtle.TLabel")
        font_label.pack(side="left", padx=(14, 6))
        self.register_tooltip(font_label, "Ladder text size.")

        font_spinbox = ttk.Spinbox(toolbar, from_=12, to=30, increment=1, textvariable=self.font_size_var, width=5, command=self.update_font_size)
        font_spinbox.pack(side="left")
        self.register_tooltip(font_spinbox, "Increase or decrease the ladder viewer font size.")

        viewer = ttk.Frame(outer, style="Card.TFrame")
        viewer.grid(row=1, column=0, sticky="nsew")
        viewer.rowconfigure(0, weight=1)
        viewer.columnconfigure(0, weight=1)

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

    def on_mode_change(self) -> None:
        if self.mode_var.get() == "online":
            self.status_var.set("Online view selected")
        else:
            self.status_var.set("Offline programming / simulation")
        self.render_ladder()

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
        if self.mode_var.get() == "online":
            tags = self.remote_snapshot.get("tags", {}) if isinstance(self.remote_snapshot, dict) else {}
            forced = self.remote_snapshot.get("forced", {}) if isinstance(self.remote_snapshot, dict) else {}
            timer_values = self.remote_snapshot.get("timers", {}) if isinstance(self.remote_snapshot, dict) else {}
            rung_power, traces = trace_program_state(
                self.program,
                tags if isinstance(tags, dict) else {},
                forced if isinstance(forced, dict) else {},
            )
            _ = rung_power
        else:
            if self.last_scan is not None:
                traces = self.last_scan.traces
                timer_values = self.last_scan.timers
            else:
                _, traces = trace_program_state(self.program, self.engine.tags, self.engine.forced)

        document = LadderRenderer(self.program, traces=traces, timer_values=timer_values).render()
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

    def on_click(self, event: tk.Event[tk.Text]) -> str:
        self.ladder_text.focus_set()
        index = self.ladder_text.index(f"@{event.x},{event.y}")
        for tag_name in reversed(self.ladder_text.tag_names(index)):
            if tag_name in self.selection_tag_to_key:
                self.selected_key = self.selection_tag_to_key[tag_name]
                self.render_ladder()
                return "break"
        return "break"

    def on_double_click(self, event: tk.Event[tk.Text]) -> str:
        self.on_click(event)
        self.edit_selected()
        return "break"

    def on_key_press(self, event: tk.Event[tk.Text]) -> str:
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
        self.last_scan = None
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
            self.last_scan = None
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
        BindingsManagerDialog(self.root, self.program)
        self.render_ladder()

    def edit_rung_comment(self) -> None:
        rung_index = self.current_rung_index()
        rung = self.program.rungs[rung_index]
        comment = simpledialog.askstring("Rung comment", "Comment", parent=self.root, initialvalue=rung.comment)
        if comment is None:
            return
        rung.comment = comment
        self.status_var.set(f"Updated comment for rung {rung_index + 1:03d}")
        self.render_ladder()

    def insert_instruction(self, before: bool) -> None:
        selection = self.current_selection()
        dialog = StepDialog(self.root, title="Insert instruction")
        if dialog.result is None:
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
        self.engine.load_program(self.program)
        self.last_scan = None
        self.status_var.set("Inserted instruction")
        self.render_ladder()

    def add_rung_after(self) -> None:
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
        selection = self.current_selection()
        if selection is None or selection.kind != "step" or selection.path is None:
            return
        rung = self.program.rungs[selection.rung_index]
        dialog = StepDialog(self.root, title="New branch instruction")

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
                self.engine.load_program(self.program)
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

        self.engine.load_program(self.program)
        self.last_scan = None
        self.status_var.set("Created branch")
        self.render_ladder()

    def edit_selected(self) -> None:
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
        container[index] = dialog.result
        self.engine.load_program(self.program)
        self.last_scan = None
        self.status_var.set("Updated instruction")
        self.render_ladder()

    def delete_selected(self) -> None:
        selection = self.current_selection()
        if selection is None:
            return
        if selection.kind == "rung":
            if not self.program.rungs:
                return
            self.program.rungs.pop(selection.rung_index)
            if not self.program.rungs:
                self.program.rungs.append(Rung(comment="", elements=[]))
            self.engine.load_program(self.program)
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
            self.engine.load_program(self.program)
            self.last_scan = None
            self.selected_key = f"rung:{selection.rung_index}"
            self.status_var.set("Deleted instruction")
            self.render_ladder()

    def step_scan(self) -> None:
        if self.mode_var.get() != "offline":
            self.status_var.set("Step is only available in offline mode")
            return
        scan_ms = max(10, int(self.scan_ms_var.get()))
        self.last_scan = self.engine.scan(scan_ms=scan_ms)
        self.status_var.set(f"Executed one offline scan ({scan_ms} ms)")
        self.render_ladder()

    def _run_tick(self) -> None:
        self.step_scan()
        self.run_job = self.root.after(max(10, int(self.scan_ms_var.get())), self._run_tick)

    def start_run(self) -> None:
        if self.mode_var.get() != "offline":
            self.status_var.set("Run is only available in offline mode")
            return
        if self.run_job is None:
            self.run_job = self.root.after(0, self._run_tick)
            self.status_var.set("Started offline simulation")

    def stop_run(self) -> None:
        if self.run_job is not None:
            self.root.after_cancel(self.run_job)
            self.run_job = None
        self.engine.reset_timers()
        self.last_scan = None
        self.status_var.set("Stopped offline simulation")
        self.render_ladder()

    def connect_demo(self) -> None:
        self.disconnect_remote(silent=True)
        try:
            session = RemoteSession(SubprocessJsonTransport())
            hello = session.hello(timeout=1.0)
        except Exception as exc:
            messagebox.showerror("Connection failed", str(exc), parent=self.root)
            return
        if not hello:
            messagebox.showerror("Connection failed", "Demo runtime did not respond.", parent=self.root)
            session.transport.close()
            return
        self.remote = session
        self.status_var.set("Connected to demo runtime")
        self.mode_var.set("online")
        self.remote_snapshot_request()

    def connect_serial(self) -> None:
        port = simpledialog.askstring("Serial port", "Port", parent=self.root, initialvalue="/dev/ttyUSB0")
        if not port:
            return
        baud = simpledialog.askinteger("Serial baud", "Baud", parent=self.root, initialvalue=115200)
        if baud is None:
            return
        self.disconnect_remote(silent=True)
        try:
            session = RemoteSession(SerialJsonTransport(port=port, baudrate=baud))
            hello = session.hello(timeout=1.0)
        except Exception as exc:
            messagebox.showerror("Serial connection failed", str(exc), parent=self.root)
            return
        if not hello:
            messagebox.showerror("Serial connection failed", "No response from target.", parent=self.root)
            return
        self.remote = session
        self.status_var.set(f"Connected to {port}")
        self.mode_var.set("online")
        self.remote_snapshot_request()

    def disconnect_remote(self, silent: bool = False) -> None:
        if self.remote is not None:
            try:
                self.remote.transport.close()
            except Exception:
                pass
        self.remote = None
        self.remote_snapshot = {}
        if self.remote_watch_job is not None:
            self.root.after_cancel(self.remote_watch_job)
            self.remote_watch_job = None
        self.auto_online_var.set(False)
        if not silent:
            self.status_var.set("Disconnected remote runtime")
        self.render_ladder()

    def require_remote(self) -> RemoteSession | None:
        if self.remote is None:
            messagebox.showinfo("Remote runtime", "Connect to a runtime first.", parent=self.root)
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
        self.render_ladder()

    def toggle_remote_watch(self) -> None:
        if not self.auto_online_var.get():
            if self.remote_watch_job is not None:
                self.root.after_cancel(self.remote_watch_job)
                self.remote_watch_job = None
            return
        self._remote_watch_tick()

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
                self.status_var.set("Lost communication with remote runtime")
                return
        self.remote_watch_job = self.root.after(500, self._remote_watch_tick)

    def set_tag_dialog(self) -> None:
        default_tag = default_tag_for_selection(self.current_selection(), self.program)
        tag = simpledialog.askstring("Set tag", "Tag", parent=self.root, initialvalue=default_tag or "")
        if not tag:
            return
        value = ask_bool(self.root, "Set tag", f"Value for {tag}", initial="1")
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
            self.status_var.set(f"Set {tag} = {int(value)}")
            self.render_ladder()

    def force_tag_dialog(self) -> None:
        default_tag = default_tag_for_selection(self.current_selection(), self.program)
        tag = simpledialog.askstring("Force tag", "Tag", parent=self.root, initialvalue=default_tag or "")
        if not tag:
            return
        value = ask_bool(self.root, "Force tag", f"Force value for {tag}", initial="1")
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
            self.status_var.set(f"Forced {tag} = {int(value)}")
            self.render_ladder()

    def unforce_tag_dialog(self) -> None:
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
            current_value = bool(tags.get(tag, False)) if isinstance(tags, dict) else False
            value = ask_bool(self.root, "Force tag", f"Force value for {tag}", initial="1" if current_value else "0")
            if value is None:
                return
            remote = self.require_remote()
            if remote is None:
                return
            remote.force_tag(tag, enabled=True, value=value, timeout=0.5)
            self.remote_snapshot_request()
            self.status_var.set(f"Forced {tag} = {int(value)}")
            return

        if tag in self.engine.forced:
            self.engine.clear_force(tag)
            self.last_scan = None
            self.status_var.set(f"Removed force from {tag}")
            self.render_ladder()
            return

        current_value = self.engine.read_tag(tag)
        value = ask_bool(self.root, "Force tag", f"Force value for {tag}", initial="1" if current_value else "0")
        if value is None:
            return
        self.engine.set_force(tag, value)
        self.last_scan = None
        self.status_var.set(f"Forced {tag} = {int(value)}")
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
