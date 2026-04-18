from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .model import Program
from .transport import JsonLineTransport


@dataclass
class RemoteSession:
    transport: JsonLineTransport

    def hello(self, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "hello", "role": "host", "version": 1})
        return self.transport.recv(timeout=timeout)

    def download_program(self, program: Program, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "download_program", "program": program.to_dict()})
        return self.transport.recv(timeout=timeout)

    def set_tag(self, tag: str, value: bool, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "set_tag", "tag": tag, "value": value})
        return self.transport.recv(timeout=timeout)

    def force_tag(self, tag: str, enabled: bool, value: bool, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "force", "tag": tag, "enabled": enabled, "value": value})
        return self.transport.recv(timeout=timeout)

    def bind_tag(
        self,
        tag: str,
        direction: str,
        address: str,
        timeout: float = 1.0,
    ) -> dict[str, Any] | None:
        self.transport.send(
            {"type": "bind", "tag": tag, "direction": direction, "address": address}
        )
        return self.transport.recv(timeout=timeout)

    def request_snapshot(self, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "snapshot_request"})
        return self.transport.recv(timeout=timeout)
