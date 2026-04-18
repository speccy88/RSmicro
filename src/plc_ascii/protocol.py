from __future__ import annotations

import json
from typing import Any


PROTOCOL_VERSION = 1


def encode_message(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


def decode_message(data: bytes) -> dict[str, Any]:
    return json.loads(data.decode("utf-8"))


def hello_message(role: str, platform: str = "python") -> dict[str, Any]:
    return {
        "type": "hello",
        "role": role,
        "version": PROTOCOL_VERSION,
        "platform": platform,
    }


def snapshot_message(
    mode: str,
    tags: dict[str, bool],
    timers: dict[str, Any],
    forced: dict[str, bool],
    rung_power: dict[str, bool] | None = None,
) -> dict[str, Any]:
    return {
        "type": "snapshot",
        "mode": mode,
        "tags": tags,
        "timers": timers,
        "forced": forced,
        "rung_power": rung_power or {},
    }
