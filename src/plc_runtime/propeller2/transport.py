from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from plc_ascii.model import Program

from .runtime import DEFAULT_SCAN_MS, Propeller2Runtime, Propeller2RuntimeError, TaqozConsole, open_serial_port


def _plc_lines(raw: str) -> list[str]:
    lines: list[str] = []
    for raw_line in raw.replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        marker = line.find("PLC ")
        if marker >= 0:
            lines.append(line[marker:].strip())
    return lines


@dataclass
class Propeller2Transport:
    port: str
    baudrate: int = 115200
    timeout: float = 0.2
    scan_ms: int = DEFAULT_SCAN_MS
    _serial: Any | None = field(init=False, default=None)
    _console: TaqozConsole | None = field(init=False, default=None)
    _pending: dict[str, Any] | None = field(init=False, default=None)
    _download_chunks: list[str] = field(init=False, default_factory=list)
    _upload_chunks: list[str] = field(init=False, default_factory=list)
    _program_cache: Program | None = field(init=False, default=None)
    _scalar_variables: list[tuple[str, str]] = field(init=False, default_factory=list)
    _timer_tags: list[str] = field(init=False, default_factory=list)
    _counter_tags: list[str] = field(init=False, default_factory=list)
    _mode: str = field(init=False, default="run")
    _runtime: Propeller2Runtime = field(init=False, default_factory=Propeller2Runtime)

    def __post_init__(self) -> None:
        self._serial = open_serial_port(self.port, baudrate=self.baudrate, timeout=self.timeout)
        self._console = TaqozConsole(self._serial)
        self._console.enter_taqoz(reset=True, timeout=2.5)

    def _send_taqoz(self, command: str, timeout: float = 2.0) -> list[str]:
        assert self._console is not None
        raw = self._console.send_command(command, timeout=timeout)
        return _plc_lines(raw)

    def _load_runtime(self, program: Program) -> None:
        assert self._console is not None
        self._console.enter_taqoz(reset=True, timeout=2.5)
        self._console.send_source(self._runtime.build_runtime_source(program, scan_ms=self.scan_ms), timeout=2.0)
        self._program_cache = program
        self._set_program_cache(program)

    def _set_program_cache(self, program: Program) -> None:
        self._program_cache = program
        self._scalar_variables = [(variable.tag, variable.data_type) for variable in program.variables if variable.data_type in {"bool", "int"}]
        self._timer_tags = list(program.timer_configs().keys())
        self._counter_tags = list(program.counter_configs().keys())

    def _fetch_program(self) -> Program:
        lines = self._send_taqoz("PLC.UPLOAD", timeout=2.0)
        chunks: list[str] = []
        in_upload = False
        for line in lines:
            if line == "PLC UPLOAD BEGIN":
                in_upload = True
                continue
            if line == "PLC UPLOAD END":
                break
            if not in_upload:
                continue
            parts = line.split(" ", 3)
            if len(parts) != 4 or parts[1] != "CHUNK":
                continue
            chunks.append(parts[3])
        if not chunks:
            raise Propeller2RuntimeError("The Propeller 2 board did not return a stored program")
        payload = bytes.fromhex("".join(chunks)).decode("utf-8")
        program = Program.from_dict(json.loads(payload))
        self._set_program_cache(program)
        return program

    def _snapshot_response(self) -> dict[str, Any]:
        if self._program_cache is None:
            self._fetch_program()
        if self._mode == "run":
            self._send_taqoz("PLC.SCAN", timeout=1.0)
        lines = self._send_taqoz("PLC.SNAPSHOT", timeout=2.0)
        mode = "run"
        tags: dict[str, Any] = {}
        timers: dict[str, dict[str, Any]] = {}
        counters: dict[str, dict[str, Any]] = {}
        forced: dict[str, Any] = {}
        for line in lines:
            parts = line.split()
            if len(parts) < 3 or parts[0] != "PLC":
                continue
            record_type = parts[1]
            if record_type == "MODE" and len(parts) >= 3:
                mode = "run" if int(parts[2]) else "stop"
                continue
            if record_type == "VAR" and len(parts) >= 4:
                index = int(parts[2])
                value = int(parts[3])
                tag, data_type = self._scalar_variables[index]
                tags[tag] = bool(value) if data_type == "bool" else value
                continue
            if record_type == "TIMER" and len(parts) >= 8:
                index = int(parts[2])
                tag = self._timer_tags[index]
                timer = {
                    "pre": int(parts[3]),
                    "acc": int(parts[4]),
                    "dn": bool(int(parts[5])),
                    "en": bool(int(parts[6])),
                    "tt": bool(int(parts[7])),
                }
                timers[tag] = timer
                tags[f"{tag}.pre"] = timer["pre"]
                tags[f"{tag}.acc"] = timer["acc"]
                tags[f"{tag}.dn"] = timer["dn"]
                tags[f"{tag}.en"] = timer["en"]
                tags[f"{tag}.tt"] = timer["tt"]
                continue
            if record_type == "COUNTER" and len(parts) >= 6:
                index = int(parts[2])
                tag = self._counter_tags[index]
                counter = {
                    "pre": int(parts[3]),
                    "acc": int(parts[4]),
                    "dn": bool(int(parts[5])),
                }
                counters[tag] = counter
                tags[f"{tag}.pre"] = counter["pre"]
                tags[f"{tag}.acc"] = counter["acc"]
                tags[f"{tag}.dn"] = counter["dn"]
                continue
        return {
            "type": "snapshot",
            "mode": mode,
            "tags": tags,
            "timers": timers,
            "counters": counters,
            "forced": forced,
            "rung_power": [],
        }

    def send(self, payload: dict) -> None:
        message_type = payload.get("type")
        if message_type == "hello":
            lines = self._send_taqoz("PLC.HELLO", timeout=1.5)
            runtime_loaded = any(line.startswith("PLC HELLO") for line in lines)
            response = {
                "type": "hello",
                "role": "device",
                "version": 1,
                "platform": "propeller2-taqoz",
            }
            if runtime_loaded:
                try:
                    self._fetch_program()
                except Exception:
                    pass
                response["runtime"] = "loaded"
            else:
                response["runtime"] = "missing"
            self._pending = response
            return
        if message_type == "download_program_begin":
            self._download_chunks = []
            self._pending = {"type": "ack", "request": "download_program_begin"}
            return
        if message_type == "download_program_chunk":
            self._download_chunks.append(str(payload.get("data", "")))
            self._pending = {"type": "ack", "request": "download_program_chunk"}
            return
        if message_type == "download_program_commit":
            serialized = "".join(self._download_chunks)
            program = Program.from_dict(json.loads(serialized))
            self._load_runtime(program)
            self._pending = {"type": "ack", "request": "download_program", "program": program.name}
            return
        if message_type == "upload_program_begin":
            program = self._fetch_program()
            serialized = json.dumps(program.to_dict(), separators=(",", ":"))
            self._upload_chunks = [serialized[index : index + 120] for index in range(0, len(serialized), 120)] or [""]
            self._pending = {"type": "upload_program_info", "chunks": len(self._upload_chunks)}
            return
        if message_type == "upload_program_chunk":
            index = int(payload.get("index", 0))
            if index < 0 or index >= len(self._upload_chunks):
                self._pending = {"type": "error", "message": "Invalid upload chunk index"}
                return
            self._pending = {"type": "upload_program_chunk", "index": index, "data": self._upload_chunks[index]}
            return
        if message_type == "upload_program_end":
            self._upload_chunks = []
            self._pending = {"type": "ack", "request": "upload_program_end"}
            return
        if message_type == "snapshot_request":
            self._pending = self._snapshot_response()
            return
        if message_type == "run":
            mode = str(payload.get("mode", "run")).lower()
            if mode == "run":
                self._send_taqoz("PLC.RUN", timeout=1.0)
            else:
                self._send_taqoz("PLC.STOP", timeout=1.0)
            self._mode = mode
            self._pending = {"type": "ack", "request": "run", "mode": mode}
            return
        if message_type == "set_tag":
            if self._program_cache is None:
                self._fetch_program()
            tag = str(payload.get("tag", ""))
            for index, (name, data_type) in enumerate(self._scalar_variables):
                if name != tag:
                    continue
                value = payload.get("value")
                raw = "1" if data_type == "bool" and bool(value) else "0" if data_type == "bool" else str(int(value))
                self._send_taqoz(f"{raw} PLC.SET.{index}", timeout=1.0)
                self._pending = {"type": "ack", "request": "set_tag", "tag": tag}
                return
            self._pending = {"type": "error", "message": f"Tag '{tag}' cannot be edited online on the Propeller 2 runtime"}
            return
        if message_type == "force":
            tag = str(payload.get("tag", ""))
            self._pending = {"type": "error", "message": f"Tag '{tag}' cannot be forced on the Propeller 2 runtime yet"}
            return
        if message_type == "bind":
            self._pending = {"type": "error", "message": "Bindings are compiled into the Propeller 2 runtime during Download"}
            return
        self._pending = {"type": "error", "message": f"Unknown message type: {message_type}"}

    def recv(self, timeout: float | None = None) -> dict | None:
        _ = timeout
        pending = self._pending
        self._pending = None
        return pending

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()
