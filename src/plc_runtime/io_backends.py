from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class IOBackend:
    def read(self, address: str) -> Any:
        raise NotImplementedError

    def write(self, address: str, value: Any) -> None:
        raise NotImplementedError


@dataclass
class MemoryIOBackend(IOBackend):
    values: dict[str, Any] = field(default_factory=dict)

    def read(self, address: str) -> Any:
        return self.values.get(address, False)

    def write(self, address: str, value: Any) -> None:
        self.values[address] = value


class BlinkaGPIOBackend(IOBackend):
    """Skeleton backend for Raspberry Pi using Blinka-compatible APIs."""

    def __init__(self) -> None:
        self._input_cache: dict[str, Any] = {}
        self._output_cache: dict[str, Any] = {}

    def read(self, address: str) -> Any:
        return self._input_cache.get(address, False)

    def write(self, address: str, value: Any) -> None:
        self._output_cache[address] = value
