"""Portable ladder runtime that stays within MicroPython-friendly syntax.

This module is imported by the desktop app for tests and copied onto the
board as ``plc_runtime_portable.py`` during MicroPython runtime install.
"""

import json


COMPARE_SYMBOLS = {
    "CMP": "==",
    "EQ": "==",
    "NE": "!=",
    "GT": ">",
    "GTE": ">=",
    "LT": "<",
    "LE": "<=",
}


def clone_value(value):
    return json.loads(json.dumps(value))


def split_timer_member(tag):
    if "." not in tag:
        return None
    base, member = tag.split(".", 1)
    return base, member.lower()


def step_compare_operator(step):
    op = str(step.get("op", "")).upper()
    if op not in COMPARE_SYMBOLS:
        return None
    if op == "CMP":
        operator = str(step.get("params", {}).get("cmp", "")).strip()
        if operator in ("==", "!=", ">", ">=", "<", "<="):
            return operator
        return "=="
    return COMPARE_SYMBOLS[op]


def normalize_node(node):
    kind = str(node.get("kind", "step")).lower()
    if kind == "branch":
        lanes = []
        for lane in node.get("lanes", []):
            lanes.append([normalize_node(child) for child in lane])
        return {"kind": "branch", "lanes": lanes}

    normalized = {
        "kind": "step",
        "op": str(node.get("op", "")).upper(),
        "tag": str(node.get("tag", "")),
        "params": dict(node.get("params", {})),
    }
    if "arg" in node and node.get("arg") is not None:
        normalized["arg"] = int(node.get("arg"))
    return normalized


def normalize_rung(rung):
    if "elements" in rung:
        elements = rung.get("elements", [])
    else:
        elements = list(rung.get("conditions", [])) + list(rung.get("actions", []))
    return {
        "comment": str(rung.get("comment", "")),
        "elements": [normalize_node(node) for node in elements],
    }


def normalize_variable(variable):
    normalized = {
        "tag": str(variable.get("tag", "")),
        "type": str(variable.get("type", variable.get("data_type", ""))).lower(),
    }
    if "initial" in variable:
        normalized["initial"] = variable.get("initial")
    if "preset" in variable:
        normalized["preset"] = int(variable.get("preset") or 0)
    return normalized


def normalize_binding(binding):
    raw_address = binding.get("address", "")
    return {
        "tag": str(binding.get("tag", "")),
        "direction": str(binding.get("direction", "")),
        "address": raw_address if isinstance(raw_address, int) else str(raw_address),
    }


def normalize_program(program):
    payload = program or {}
    return {
        "name": str(payload.get("name", "device")),
        "runtime_target": str(payload.get("runtime_target", "micropython") or "micropython"),
        "rungs": [normalize_rung(rung) for rung in payload.get("rungs", [])],
        "variables": [normalize_variable(variable) for variable in payload.get("variables", [])],
        "bindings": [normalize_binding(binding) for binding in payload.get("bindings", [])],
    }


def program_variable_map(program):
    result = {}
    for variable in program.get("variables", []):
        result[variable["tag"]] = variable
    return result


def walk_steps(nodes):
    steps = []
    for node in nodes:
        if node.get("kind", "step") == "branch":
            for lane in node.get("lanes", []):
                steps.extend(walk_steps(lane))
        else:
            steps.append(node)
    return steps


def timer_configs(program):
    configs = {}
    variable_map = program_variable_map(program)
    for variable in program.get("variables", []):
        if variable.get("type") == "timer":
            configs[variable["tag"]] = int(variable.get("preset") or 0)
    for rung in program.get("rungs", []):
        for step in walk_steps(rung.get("elements", [])):
            if step.get("op") == "TON":
                variable = variable_map.get(step.get("tag"))
                preset = step.get("arg", 0)
                if variable and variable.get("type") == "timer":
                    preset = variable.get("preset", preset)
                configs[str(step.get("tag", ""))] = int(preset or 0)
    return configs


def counter_configs(program):
    configs = {}
    variable_map = program_variable_map(program)
    for variable in program.get("variables", []):
        if variable.get("type") == "counter":
            configs[variable["tag"]] = int(variable.get("preset") or 0)
    for rung in program.get("rungs", []):
        for step in walk_steps(rung.get("elements", [])):
            if step.get("op") in ("CTU", "CTD"):
                variable = variable_map.get(step.get("tag"))
                preset = step.get("arg", 0)
                if variable and variable.get("type") == "counter":
                    preset = variable.get("preset", preset)
                configs[str(step.get("tag", ""))] = int(preset or 0)
    return configs


def snapshot_message(runtime):
    return {
        "type": "snapshot",
        "mode": runtime.mode,
        "tags": runtime.sorted_copy(runtime.tags),
        "timers": runtime.sorted_copy(runtime.timers),
        "counters": runtime.sorted_copy(runtime.counters),
        "forced": runtime.sorted_copy(runtime.forced),
        "rung_power": list(runtime.last_rung_power),
    }


class MemoryStorage:
    def __init__(self):
        self.program = None

    def load_program(self):
        return clone_value(self.program) if self.program is not None else None

    def save_program(self, program):
        self.program = clone_value(program)

    def delete_program(self):
        self.program = None


def blank_program():
    return {
        "name": "device",
        "runtime_target": "micropython",
        "rungs": [],
        "variables": [],
        "bindings": [],
    }


class PortableRuntime:
    def __init__(self, backend, storage=None):
        self.backend = backend
        self.storage = storage or MemoryStorage()
        self.mode = "run"
        self.program_loaded = False
        self.program = blank_program()
        self.tags = {}
        self.forced = {}
        self.timers = {}
        self.counters = {}
        self.edge_memory = {}
        self.last_rung_power = []
        self.download_chunks = []
        self.upload_chunks = []
        stored = self.storage.load_program()
        if stored is not None:
            self.load_program(stored, persist=False)
        else:
            self.clear_program(persist=False)

    def sorted_copy(self, mapping):
        result = {}
        for key in sorted(mapping):
            result[key] = clone_value(mapping[key])
        return result

    def find_binding(self, tag):
        for binding in self.program.get("bindings", []):
            if binding.get("tag") == tag:
                return binding
        return None

    def restore_initial_values(self):
        self.tags = {}
        self.edge_memory = {}
        self.timers = {}
        self.counters = {}

        for variable in self.program.get("variables", []):
            tag = variable.get("tag", "")
            var_type = variable.get("type")
            if var_type in ("bool", "int", "float"):
                if "initial" in variable:
                    self.tags[tag] = variable.get("initial")
                elif var_type == "bool":
                    self.tags[tag] = False
                elif var_type == "float":
                    self.tags[tag] = 0.0
                else:
                    self.tags[tag] = 0

        for tag, preset in timer_configs(self.program).items():
            self.timers[tag] = {"pre": int(preset), "acc": 0, "dn": False, "en": False, "tt": False}

        for tag, preset in counter_configs(self.program).items():
            self.counters[tag] = {"pre": int(preset), "acc": 0, "dn": False}

        self.sync_composites()
        self.last_rung_power = [False for _ in self.program.get("rungs", [])]

    def load_program(self, program, persist=True):
        self.program = normalize_program(program)
        self.program_loaded = True
        self.restore_initial_values()
        if persist:
            self.storage.save_program(self.program)

    def clear_program(self, persist=True):
        self.program = blank_program()
        self.program_loaded = False
        self.restore_initial_values()
        if persist and hasattr(self.storage, "delete_program"):
            self.storage.delete_program()

    def upload_program(self):
        program = clone_value(self.program)

        for variable in program.get("variables", []):
            tag = str(variable.get("tag", ""))
            var_type = variable.get("type")
            if var_type in ("bool", "int", "float") and tag in self.tags:
                variable["initial"] = clone_value(self.tags[tag])
            elif var_type == "timer" and tag in self.timers:
                variable["preset"] = int(self.timers[tag].get("pre", variable.get("preset", 0)))
            elif var_type == "counter" and tag in self.counters:
                variable["preset"] = int(self.counters[tag].get("pre", variable.get("preset", 0)))

        for rung in program.get("rungs", []):
            for step in walk_steps(rung.get("elements", [])):
                op = step.get("op")
                tag = str(step.get("tag", ""))
                if op == "TON" and tag in self.timers:
                    step["arg"] = int(self.timers[tag].get("pre", step.get("arg", 0)))
                elif op in ("CTU", "CTD") and tag in self.counters:
                    step["arg"] = int(self.counters[tag].get("pre", step.get("arg", 0)))

        return program

    def sync_timer(self, tag):
        timer = self.timers.get(tag)
        if not timer:
            return
        self.tags[tag + ".pre"] = int(timer.get("pre", 0))
        self.tags[tag + ".acc"] = int(timer.get("acc", 0))
        self.tags[tag + ".dn"] = bool(timer.get("dn", False))
        self.tags[tag + ".en"] = bool(timer.get("en", False))
        self.tags[tag + ".tt"] = bool(timer.get("tt", False))

    def sync_counter(self, tag):
        counter = self.counters.get(tag)
        if not counter:
            return
        self.tags[tag + ".pre"] = int(counter.get("pre", 0))
        self.tags[tag + ".acc"] = int(counter.get("acc", 0))
        self.tags[tag + ".dn"] = bool(counter.get("dn", False))

    def sync_composites(self):
        for tag in self.timers:
            self.sync_timer(tag)
        for tag in self.counters:
            self.sync_counter(tag)

    def read_tag(self, tag):
        if tag in self.forced:
            return self.forced[tag]
        parts = split_timer_member(tag)
        if parts:
            base, member = parts
            timer = self.timers.get(base)
            if timer is not None:
                return timer.get(member, False)
            counter = self.counters.get(base)
            if counter is not None:
                return counter.get(member, False)
        return self.tags.get(tag, False)

    def resolve_operand(self, operand):
        if isinstance(operand, str):
            return self.read_tag(operand)
        return operand

    def write_tag(self, tag, value):
        if tag in self.forced:
            self.tags[tag] = self.forced[tag]
            return
        self.tags[tag] = value

    def set_tag(self, tag, value):
        self.tags[tag] = value

    def set_value(self, tag, value):
        parts = split_timer_member(tag)
        if parts:
            base, member = parts
            timer = self.timers.get(base)
            if timer is not None:
                if member == "pre":
                    timer["pre"] = int(value)
                    if int(timer["acc"]) > int(timer["pre"]):
                        timer["acc"] = int(timer["pre"])
                    timer["dn"] = int(timer["acc"]) >= int(timer["pre"])
                    timer["tt"] = bool(timer["en"]) and not bool(timer["dn"])
                elif member == "acc":
                    timer["acc"] = max(0, min(int(value), int(timer["pre"])))
                    timer["dn"] = int(timer["acc"]) >= int(timer["pre"])
                    timer["tt"] = bool(timer["en"]) and not bool(timer["dn"])
                elif member == "dn":
                    timer["dn"] = bool(value)
                elif member == "en":
                    timer["en"] = bool(value)
                elif member == "tt":
                    timer["tt"] = bool(value)
                self.sync_timer(base)
                return
            counter = self.counters.get(base)
            if counter is not None:
                if member == "pre":
                    counter["pre"] = int(value)
                elif member == "acc":
                    counter["acc"] = int(value)
                elif member == "dn":
                    counter["dn"] = bool(value)
                counter["dn"] = int(counter["acc"]) == int(counter["pre"])
                self.sync_counter(base)
                return
        self.set_tag(tag, value)

    def set_force(self, tag, value):
        self.forced[tag] = value
        self.tags[tag] = value

    def clear_force(self, tag):
        if tag in self.forced:
            del self.forced[tag]

    def apply_inputs(self):
        for binding in self.program.get("bindings", []):
            if binding.get("direction") == "input":
                self.set_tag(binding.get("tag", ""), self.backend.read(binding.get("address", "")))

    def apply_outputs(self):
        for binding in self.program.get("bindings", []):
            if binding.get("direction") == "output":
                self.backend.write(binding.get("address", ""), self.read_tag(binding.get("tag", "")))

    def apply_compare(self, left, right, operator):
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
        return False

    def binary_numeric_result(self, left, right, op):
        if op == "ADD":
            return left + right
        if op == "SUB":
            return left - right
        if op == "MUL":
            return left * right
        if op == "DIV":
            return left / right
        return 0

    def evaluate_power(self, step, power_in):
        op = step.get("op")
        tag = step.get("tag", "")
        if op == "XIC":
            return bool(power_in) and bool(self.read_tag(tag))
        if op == "XIO":
            return bool(power_in) and (not bool(self.read_tag(tag)))
        operator = step_compare_operator(step)
        if operator is not None:
            params = step.get("params", {})
            left = self.resolve_operand(params.get("left"))
            right = self.resolve_operand(params.get("right"))
            return bool(power_in) and self.apply_compare(left, right, operator)
        return bool(power_in)

    def prime_counter_edges_in_nodes(self, nodes, power_in, prefix=()):
        current = bool(power_in)
        for index, node in enumerate(nodes):
            if node.get("kind", "step") == "branch":
                outputs = []
                for lane_index, lane in enumerate(node.get("lanes", [])):
                    lane_power = self.prime_counter_edges_in_nodes(lane, current, prefix + (index, lane_index))
                    outputs.append(bool(lane_power))
                current = any(outputs) if outputs else current
                continue
            step_key = ".".join([str(part) for part in prefix + (index,)])
            if node.get("op") in ("CTU", "CTD"):
                self.edge_memory[step_key] = bool(current)
            current = self.evaluate_power(node, current)
        return current

    def prime_counter_edges(self):
        self.edge_memory = {}
        for rung in self.program.get("rungs", []):
            self.prime_counter_edges_in_nodes(rung.get("elements", []), True)

    def execute_step(self, step, power_in, scan_ms, step_key):
        op = step.get("op")
        tag = step.get("tag", "")
        if op == "XIC":
            return power_in and bool(self.read_tag(tag))
        if op == "XIO":
            return power_in and (not bool(self.read_tag(tag)))
        operator = step_compare_operator(step)
        if operator is not None:
            params = step.get("params", {})
            left = self.resolve_operand(params.get("left"))
            right = self.resolve_operand(params.get("right"))
            return power_in and self.apply_compare(left, right, operator)
        if op == "OTE":
            self.write_tag(tag, bool(power_in))
            return power_in
        if op == "OTL":
            if power_in:
                self.write_tag(tag, True)
            return power_in
        if op == "OTU":
            if power_in:
                self.write_tag(tag, False)
            return power_in
        if op == "CTU":
            counter = self.counters.setdefault(tag, {"pre": int(step.get("arg") or 0), "acc": 0, "dn": False})
            if "arg" in step and step.get("arg") is not None:
                counter["pre"] = max(0, int(step.get("arg") or 0))
            previous = bool(self.edge_memory.get(step_key, False))
            if power_in and not previous:
                counter["acc"] = min(int(counter["pre"]), int(counter["acc"]) + 1)
            counter["dn"] = int(counter["acc"]) == int(counter["pre"])
            self.edge_memory[step_key] = bool(power_in)
            self.sync_counter(tag)
            return power_in
        if op == "CTD":
            counter = self.counters.setdefault(tag, {"pre": int(step.get("arg") or 0), "acc": 0, "dn": False})
            if "arg" in step and step.get("arg") is not None:
                counter["pre"] = max(0, int(step.get("arg") or 0))
            previous = bool(self.edge_memory.get(step_key, False))
            if power_in and not previous:
                counter["acc"] = max(0, int(counter["acc"]) - 1)
            counter["dn"] = int(counter["acc"]) == int(counter["pre"])
            self.edge_memory[step_key] = bool(power_in)
            self.sync_counter(tag)
            return power_in
        if op == "MOV" and power_in:
            self.write_tag(tag, self.resolve_operand(step.get("params", {}).get("source")))
            return power_in
        if op == "CLR" and power_in:
            if tag in self.timers:
                self.timers[tag] = {"pre": int(self.timers[tag].get("pre", 0)), "acc": 0, "dn": False, "en": False, "tt": False}
                self.sync_timer(tag)
            elif tag in self.counters:
                self.counters[tag]["acc"] = 0
                self.counters[tag]["dn"] = False
                self.sync_counter(tag)
            else:
                self.write_tag(tag, 0)
            return power_in
        if op == "ABS" and power_in:
            self.write_tag(tag, abs(self.resolve_operand(step.get("params", {}).get("source"))))
            return power_in
        if op == "NEG" and power_in:
            self.write_tag(tag, -self.resolve_operand(step.get("params", {}).get("source")))
            return power_in
        if op in ("ADD", "SUB", "MUL", "DIV") and power_in:
            params = step.get("params", {})
            left = self.resolve_operand(params.get("left"))
            right = self.resolve_operand(params.get("right"))
            self.write_tag(tag, self.binary_numeric_result(left, right, op))
            return power_in
        if op == "TON":
            timer = self.timers.setdefault(tag, {"pre": int(step.get("arg") or 0), "acc": 0, "dn": False, "en": False, "tt": False})
            if "arg" in step and step.get("arg") is not None:
                timer["pre"] = int(step.get("arg") or 0)
            timer["en"] = bool(power_in)
            if power_in:
                timer["acc"] = min(int(timer["pre"]), int(timer["acc"]) + max(0, int(scan_ms)))
                timer["dn"] = int(timer["acc"]) >= int(timer["pre"])
                timer["tt"] = not bool(timer["dn"])
            else:
                timer["acc"] = 0
                timer["dn"] = False
                timer["tt"] = False
            self.sync_timer(tag)
            return power_in
        return power_in

    def execute_nodes(self, nodes, power_in, scan_ms, prefix=()):
        current = bool(power_in)
        for index, node in enumerate(nodes):
            if node.get("kind", "step") == "branch":
                outputs = []
                for lane_index, lane in enumerate(node.get("lanes", [])):
                    lane_power = self.execute_nodes(lane, current, scan_ms, prefix + (index, lane_index))
                    outputs.append(bool(lane_power))
                current = any(outputs) if outputs else current
                continue
            step_key = ".".join([str(part) for part in prefix + (index,)])
            current = bool(self.execute_step(node, current, scan_ms, step_key))
        return current

    def scan_once(self, scan_ms):
        self.apply_inputs()
        rung_power = []
        for rung in self.program.get("rungs", []):
            rung_power.append(bool(self.execute_nodes(rung.get("elements", []), True, scan_ms)))
        self.apply_outputs()
        for tag, forced_value in self.forced.items():
            self.tags[tag] = forced_value
        self.sync_composites()
        self.last_rung_power = rung_power
        return snapshot_message(self)

    def snapshot(self):
        self.sync_composites()
        return snapshot_message(self)

    def handle_message(self, payload):
        message_type = payload.get("type")
        if message_type == "hello":
            return {
                "type": "hello",
                "role": "device",
                "version": 1,
                "platform": "micropython",
                "mode": self.mode,
                "program_loaded": self.program_loaded,
            }
        if message_type == "download_program":
            self.load_program(payload.get("program", {}), persist=True)
            return {"type": "ack", "request": "download_program", "program": self.program.get("name", "")}
        if message_type == "download_program_begin":
            self.download_chunks = []
            return {"type": "ack", "request": "download_program_begin"}
        if message_type == "download_program_chunk":
            self.download_chunks.append(str(payload.get("data", "")))
            return {"type": "ack", "request": "download_program_chunk"}
        if message_type == "download_program_commit":
            serialized = "".join(self.download_chunks)
            self.download_chunks = []
            self.load_program(json.loads(serialized), persist=True)
            return {"type": "ack", "request": "download_program", "program": self.program.get("name", "")}
        if message_type == "upload_program":
            return {"type": "program", "program": self.upload_program()}
        if message_type == "upload_program_begin":
            serialized = json.dumps(self.upload_program(), separators=(",", ":"))
            self.upload_chunks = [serialized[index : index + 120] for index in range(0, len(serialized), 120)] or [""]
            return {"type": "upload_program_info", "chunks": len(self.upload_chunks)}
        if message_type == "upload_program_chunk":
            index = int(payload.get("index", 0))
            if index < 0 or index >= len(self.upload_chunks):
                return {"type": "error", "message": "Invalid upload chunk index"}
            return {"type": "upload_program_chunk", "index": index, "data": self.upload_chunks[index]}
        if message_type == "upload_program_end":
            self.upload_chunks = []
            return {"type": "ack", "request": "upload_program_end"}
        if message_type == "set_tag":
            tag = str(payload.get("tag", ""))
            value = payload.get("value")
            binding = self.find_binding(tag)
            if binding is not None and binding.get("direction") == "input":
                self.backend.write(binding.get("address", ""), value)
            self.set_value(tag, value)
            return {"type": "ack", "request": "set_tag", "tag": tag}
        if message_type == "force":
            tag = str(payload.get("tag", ""))
            if payload.get("enabled"):
                self.set_force(tag, payload.get("value"))
            else:
                self.clear_force(tag)
            return {"type": "ack", "request": "force", "tag": tag}
        if message_type == "bind":
            tag = str(payload.get("tag", ""))
            binding = {
                "tag": tag,
                "direction": str(payload.get("direction", "")),
                "address": str(payload.get("address", "")),
            }
            bindings = [current for current in self.program.get("bindings", []) if current.get("tag") != tag]
            bindings.append(binding)
            self.program["bindings"] = bindings
            self.program_loaded = True
            self.storage.save_program(self.program)
            return {"type": "ack", "request": "bind", "tag": tag}
        if message_type == "run":
            next_mode = str(payload.get("mode", "run"))
            if next_mode == "run" and self.mode != "run":
                self.prime_counter_edges()
            self.mode = next_mode
            return {"type": "ack", "request": "run", "mode": self.mode}
        if message_type == "scan_once":
            return self.scan_once(int(payload.get("scan_ms", 0)))
        if message_type == "snapshot_request":
            return self.snapshot()
        return {"type": "error", "message": "Unknown message type: " + str(message_type)}
