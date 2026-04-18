from __future__ import annotations

from typing import Protocol


class JsonLineTransport(Protocol):
    def send(self, payload: dict) -> None:
        ...

    def recv(self, timeout: float | None = None) -> dict | None:
        ...

    def close(self) -> None:
        ...
