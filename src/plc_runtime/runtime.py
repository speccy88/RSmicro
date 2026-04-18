from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass, field
from typing import Any

from plc_ascii.engine import LadderEngine
from plc_ascii.model import Binding, Program
from plc_ascii.protocol import hello_message, snapshot_message

from .io_backends import IOBackend, MemoryIOBackend


@dataclass
class DeviceRuntime:
    backend: IOBackend = field(default_factory=MemoryIOBackend)
    program: Program = field(default_factory=lambda: Program(name="device"))
    mode: str = "stop"

    def __post_init__(self) -> None:
        self.engine = LadderEngine(self.program)

    def load_program(self, program: Program) -> None:
        self.program = program
        self.engine.load_program(program)

    def find_binding(self, tag: str) -> Binding | None:
        for binding in self.program.bindings:
            if binding.tag == tag:
                return binding
        return None

    def apply_inputs(self) -> None:
        for binding in self.program.bindings:
            if binding.direction == "input":
                self.engine.set_tag(binding.tag, self.backend.read(binding.address))

    def apply_outputs(self) -> None:
        for binding in self.program.bindings:
            if binding.direction == "output":
                self.backend.write(binding.address, self.engine.read_tag(binding.tag))

    def scan_once(self, scan_ms: int = 100) -> dict[str, Any]:
        self.apply_inputs()
        result = self.engine.scan(scan_ms=scan_ms)
        self.apply_outputs()
        return snapshot_message(
            mode=self.mode,
            tags=result.tags,
            timers=result.timers,
            counters=result.counters,
            forced=dict(self.engine.forced),
            rung_power=result.rung_power,
        )

    def handle_message(self, payload: dict[str, Any]) -> dict[str, Any]:
        message_type = payload.get("type")

        if message_type == "hello":
            return hello_message(role="device", platform="python-runtime")
        if message_type == "download_program":
            self.load_program(Program.from_dict(payload["program"]))
            return {"type": "ack", "request": "download_program", "program": self.program.name}
        if message_type == "set_tag":
            tag = str(payload["tag"])
            value = payload["value"]
            binding = self.find_binding(tag)
            if binding is not None:
                self.backend.write(binding.address, value)
            self.engine.set_tag(tag, value)
            return {"type": "ack", "request": "set_tag", "tag": tag}
        if message_type == "force":
            tag = str(payload["tag"])
            if bool(payload["enabled"]):
                self.engine.set_force(tag, payload["value"])
            else:
                self.engine.clear_force(tag)
            return {"type": "ack", "request": "force", "tag": tag}
        if message_type == "bind":
            binding = Binding(
                tag=str(payload["tag"]),
                direction=str(payload["direction"]),
                address=str(payload["address"]),
            )
            binding.validate()
            self.program.bindings = [current for current in self.program.bindings if current.tag != binding.tag]
            self.program.bindings.append(binding)
            return {"type": "ack", "request": "bind", "tag": binding.tag}
        if message_type == "run":
            self.mode = str(payload.get("mode", "run"))
            return {"type": "ack", "request": "run", "mode": self.mode}
        if message_type == "scan_once":
            return self.scan_once(scan_ms=int(payload.get("scan_ms", 100)))
        if message_type == "snapshot_request":
            return self.scan_once(scan_ms=0)

        return {"type": "error", "message": f"Unknown message type: {message_type}"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PLC runtime environment")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run a simple stdin/stdout JSON-line runtime for local testing",
    )
    return parser


def run_demo() -> None:
    runtime = DeviceRuntime()
    print("# PLC runtime demo ready", file=sys.stderr)
    for line in sys.stdin:
        raw = line.strip()
        if not raw:
            continue
        import json

        payload = json.loads(raw)
        response = runtime.handle_message(payload)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.demo:
        run_demo()
        return

    runtime = DeviceRuntime()
    while True:
        if runtime.mode == "run":
            runtime.scan_once()
        time.sleep(0.1)


if __name__ == "__main__":
    main()
