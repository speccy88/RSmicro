from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from plc_ascii.model import Program
from plc_runtime.base import BoardRuntime


DEFAULT_CONFIG = {
    "scan_ms": 50,
    "input_pulls": {},
    "active_low_inputs": [],
}


class MicroPythonRuntime(BoardRuntime):
    target_name = "MicroPython"

    def default_config(self) -> dict[str, Any]:
        return json.loads(json.dumps(DEFAULT_CONFIG))

    def merge_config(self, config: dict[str, Any] | None) -> dict[str, Any]:
        merged = self.default_config()
        if not config:
            return merged
        for key, value in config.items():
            if key == "input_pulls" and isinstance(value, dict):
                merged[key].update(value)
            elif key == "active_low_inputs" and isinstance(value, list):
                merged[key] = list(value)
            else:
                merged[key] = value
        return merged

    def board_files(self, program: Program | None = None, **kwargs: Any) -> dict[str, str]:
        config = kwargs.get("config")
        include_program = bool(kwargs.get("include_program", False))
        payload_config = self.merge_config(config)
        bundle = {
            "plc_runtime_portable.py": self.resource_text("plc_runtime_portable.py"),
            "plc_runtime_board.py": self.resource_text("plc_runtime_board.py"),
            "plc_runtime_config.json": json.dumps(payload_config, indent=2),
            "main.py": self.resource_text("main.py"),
        }
        if include_program:
            payload_program = (
                program.to_dict()
                if program is not None
                else {"name": "device", "runtime_target": "micropython", "rungs": [], "variables": [], "bindings": []}
            )
            bundle["plc_program.json"] = json.dumps(payload_program, indent=2)
        return bundle

    def build_runtime_bundle(
        self,
        program: Program | None = None,
        config: dict[str, Any] | None = None,
        *,
        include_program: bool = False,
    ) -> dict[str, str]:
        return self.board_files(program, config=config, include_program=include_program)

    def _run_mpremote(self, port: str, *args: str) -> None:
        command = ["mpremote", "connect", f"port:{port}", *args]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            return
        details = result.stderr.strip() or result.stdout.strip() or f"Command failed: {' '.join(command)}"
        raise RuntimeError(details)

    def _remove_program(self, port: str) -> None:
        try:
            self._run_mpremote(port, "fs", "rm", ":plc_program.json")
        except Exception as exc:
            details = str(exc).lower()
            if "enoent" in details or "no such file" in details or "could not stat path" in details:
                return
            raise

    def install(
        self,
        port: str,
        *,
        program: Program | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        _ = program
        bundle = self.build_runtime_bundle(config=config, include_program=False)
        upload_order = [
            "plc_runtime_portable.py",
            "plc_runtime_board.py",
            "plc_runtime_config.json",
            "main.py",
        ]
        with tempfile.TemporaryDirectory(prefix="plc-micropython-") as tempdir:
            temp_root = Path(tempdir)
            for remote_name in upload_order:
                local_path = temp_root / remote_name
                local_path.write_text(bundle[remote_name], encoding="utf-8")
                self._run_mpremote(port, "fs", "cp", str(local_path), f":{remote_name}")
            self._remove_program(port)
            self._run_mpremote(port, "soft-reset")


_RUNTIME = MicroPythonRuntime()


def default_config() -> dict[str, Any]:
    return _RUNTIME.default_config()


def merge_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return _RUNTIME.merge_config(config)


def build_runtime_bundle(
    program: Program | None = None,
    config: dict[str, Any] | None = None,
    *,
    include_program: bool = False,
) -> dict[str, str]:
    return _RUNTIME.build_runtime_bundle(program, config, include_program=include_program)


def install_runtime(
    port: str,
    *,
    program: Program | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    _RUNTIME.install(port, program=program, config=config)
