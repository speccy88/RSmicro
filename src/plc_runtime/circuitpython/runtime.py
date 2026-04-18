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
    "input_pulls": {"IO0": "up"},
    "active_low_inputs": ["IO0"],
}


class CircuitPythonRuntime(BoardRuntime):
    target_name = "CircuitPython"

    def default_config(self) -> dict[str, Any]:
        return json.loads(json.dumps(DEFAULT_CONFIG))

    def merge_config(self, config: dict[str, Any] | None) -> dict[str, Any]:
        merged = self.default_config()
        if not config:
            return merged
        for key, value in config.items():
            if key in {"input_pulls"} and isinstance(value, dict):
                merged[key].update(value)
            elif key in {"active_low_inputs"} and isinstance(value, list):
                merged[key] = list(value)
            else:
                merged[key] = value
        return merged

    def board_files(self, program: Program | None = None, **kwargs: Any) -> dict[str, str]:
        config = kwargs.get("config")
        payload_program = (
            program.to_dict()
            if program is not None
            else {"name": "device", "rungs": [], "variables": [], "bindings": []}
        )
        payload_config = self.merge_config(config)
        return {
            "plc_runtime_portable.py": self.resource_text("plc_runtime_portable.py"),
            "plc_runtime_board.py": self.resource_text("plc_runtime_board.py"),
            "plc_runtime_config.json": json.dumps(payload_config, indent=2),
            "plc_program.json": json.dumps(payload_program, indent=2),
            "code.py": self.resource_text("code.py"),
        }

    def build_runtime_bundle(
        self,
        program: Program | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        return self.board_files(program, config=config)

    def _run_ampy(self, port: str, *args: str) -> None:
        command = ["ampy", "--port", port, "--delay", "1", *args]
        result = subprocess.run(command, capture_output=True, text=True, timeout=45)
        if result.returncode == 0:
            return
        details = result.stderr.strip() or result.stdout.strip() or f"Command failed: {' '.join(command)}"
        raise RuntimeError(details)

    @staticmethod
    def _mounted_circuitpython_volume() -> Path | None:
        volumes_root = Path("/Volumes")
        if not volumes_root.exists():
            return None
        preferred = volumes_root / "CIRCUITPY"
        if preferred.exists() and preferred.is_dir():
            return preferred
        for candidate in sorted(volumes_root.iterdir()):
            if not candidate.is_dir():
                continue
            if (candidate / "boot_out.txt").exists():
                return candidate
        return None

    def _install_via_volume(self, bundle: dict[str, str]) -> Path:
        volume = self._mounted_circuitpython_volume()
        if volume is None:
            raise RuntimeError(
                "CircuitPython reports a read-only filesystem over serial, and no mounted CIRCUITPY volume was found. "
                "Mount the board on your computer or make the filesystem writable from CircuitPython before retrying."
            )
        for remote_name, content in bundle.items():
            (volume / remote_name).write_text(content, encoding="utf-8")
        return volume

    def install(
        self,
        port: str,
        *,
        program: Program | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        bundle = self.build_runtime_bundle(program, config)
        upload_order = [
            "plc_runtime_portable.py",
            "plc_runtime_board.py",
            "plc_runtime_config.json",
            "plc_program.json",
            "code.py",
        ]
        with tempfile.TemporaryDirectory(prefix="plc-circuitpython-") as tempdir:
            temp_root = Path(tempdir)
            try:
                for remote_name in upload_order:
                    local_path = temp_root / remote_name
                    local_path.write_text(bundle[remote_name], encoding="utf-8")
                    self._run_ampy(port, "put", str(local_path), remote_name)
                self._run_ampy(port, "reset")
                return
            except Exception as exc:
                if "Read-only filesystem" not in str(exc):
                    raise
            volume = self._install_via_volume(bundle)
            try:
                self._run_ampy(port, "reset")
            except Exception:
                pass
            return volume


_RUNTIME = CircuitPythonRuntime()


def default_config() -> dict[str, Any]:
    return _RUNTIME.default_config()


def merge_config(config: dict[str, Any] | None) -> dict[str, Any]:
    return _RUNTIME.merge_config(config)


def build_runtime_bundle(program: Program | None = None, config: dict[str, Any] | None = None) -> dict[str, str]:
    return _RUNTIME.build_runtime_bundle(program, config)


def install_runtime(
    port: str,
    *,
    program: Program | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    _RUNTIME.install(port, program=program, config=config)
