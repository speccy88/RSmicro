from __future__ import annotations

import inspect
import json
import subprocess
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any

from . import circuitpython_portable_runtime
from .model import Program


DEFAULT_CONFIG = {
    "scan_ms": 50,
    "input_pulls": {"IO0": "up"},
    "active_low_inputs": ["IO0"],
}


def _asset_text(name: str) -> str:
    asset_root = resources.files("plc_ascii") / "circuitpython_assets"
    return asset_root.joinpath(name).read_text(encoding="utf-8")


def default_config() -> dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_CONFIG))


def merge_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = default_config()
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


def build_runtime_bundle(program: Program | None = None, config: dict[str, Any] | None = None) -> dict[str, str]:
    payload_program = program.to_dict() if program is not None else {"name": "device", "rungs": [], "variables": [], "bindings": []}
    payload_config = merge_config(config)
    return {
        "plc_runtime_portable.py": inspect.getsource(circuitpython_portable_runtime),
        "plc_runtime_board.py": _asset_text("plc_runtime_board.py"),
        "plc_runtime_config.json": json.dumps(payload_config, indent=2),
        "plc_program.json": json.dumps(payload_program, indent=2),
        "code.py": _asset_text("code.py"),
    }


def _run_ampy(port: str, *args: str) -> None:
    command = ["ampy", "--port", port, "--delay", "1", *args]
    result = subprocess.run(command, capture_output=True, text=True, timeout=45)
    if result.returncode == 0:
        return
    details = result.stderr.strip() or result.stdout.strip() or f"Command failed: {' '.join(command)}"
    raise RuntimeError(details)


def install_runtime(
    port: str,
    *,
    program: Program | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    bundle = build_runtime_bundle(program, config)
    upload_order = [
        "plc_runtime_portable.py",
        "plc_runtime_board.py",
        "plc_runtime_config.json",
        "plc_program.json",
        "code.py",
    ]
    with tempfile.TemporaryDirectory(prefix="plc-circuitpython-") as tempdir:
        temp_root = Path(tempdir)
        for remote_name in upload_order:
            local_path = temp_root / remote_name
            local_path.write_text(bundle[remote_name], encoding="utf-8")
            _run_ampy(port, "put", str(local_path), remote_name)
        _run_ampy(port, "reset")
