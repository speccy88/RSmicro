from __future__ import annotations

import json
from pathlib import Path

from .model import Program


def load_program(path: str | Path) -> Program:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return Program.from_dict(payload)


def save_program(program: Program, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(program.to_dict(), indent=2), encoding="utf-8")
