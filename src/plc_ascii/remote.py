from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from .model import Program
from .transport import JsonLineTransport

PROGRAM_CHUNK_SIZE = 120


@dataclass
class RemoteSession:
    transport: JsonLineTransport

    def hello(self, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "hello", "role": "host", "version": 1})
        return self.transport.recv(timeout=timeout)

    def download_program(self, program: Program, timeout: float = 1.0) -> dict[str, Any] | None:
        serialized = json.dumps(program.to_dict(), separators=(",", ":"))
        self.transport.send({"type": "download_program_begin", "chunks": max(1, (len(serialized) + PROGRAM_CHUNK_SIZE - 1) // PROGRAM_CHUNK_SIZE)})
        response = self.transport.recv(timeout=timeout)
        if response is None or response.get("type") == "error":
            return response
        for index in range(0, len(serialized), PROGRAM_CHUNK_SIZE):
            chunk = serialized[index : index + PROGRAM_CHUNK_SIZE]
            self.transport.send({"type": "download_program_chunk", "data": chunk})
            response = self.transport.recv(timeout=timeout)
            if response is None or response.get("type") == "error":
                return response
        self.transport.send({"type": "download_program_commit"})
        return self.transport.recv(timeout=timeout)

    def upload_program(self, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "upload_program_begin"})
        response = self.transport.recv(timeout=timeout)
        if response is None or response.get("type") == "error":
            return response
        if response.get("type") == "program":
            return response
        if response.get("type") != "upload_program_info":
            return response
        chunks = int(response.get("chunks", 0))
        serialized_parts: list[str] = []
        for index in range(chunks):
            self.transport.send({"type": "upload_program_chunk", "index": index})
            chunk_response = self.transport.recv(timeout=timeout)
            if chunk_response is None or chunk_response.get("type") == "error":
                return chunk_response
            serialized_parts.append(str(chunk_response.get("data", "")))
        self.transport.send({"type": "upload_program_end"})
        self.transport.recv(timeout=timeout)
        program_payload = json.loads("".join(serialized_parts))
        return {"type": "program", "program": program_payload}

    def set_tag(self, tag: str, value: Any, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "set_tag", "tag": tag, "value": value})
        return self.transport.recv(timeout=timeout)

    def force_tag(self, tag: str, enabled: bool, value: Any, timeout: float = 1.0) -> dict[str, Any] | None:
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

    def set_mode(self, mode: str, timeout: float = 1.0) -> dict[str, Any] | None:
        self.transport.send({"type": "run", "mode": mode})
        return self.transport.recv(timeout=timeout)
