from __future__ import annotations

from dataclasses import dataclass, field


class IOBackend:
    def read(self, address: str) -> bool:
        raise NotImplementedError

    def write(self, address: str, value: bool) -> None:
        raise NotImplementedError


@dataclass
class MemoryIOBackend(IOBackend):
    values: dict[str, bool] = field(default_factory=dict)

    def read(self, address: str) -> bool:
        return bool(self.values.get(address, False))

    def write(self, address: str, value: bool) -> None:
        self.values[address] = bool(value)


class BlinkaGPIOBackend(IOBackend):
    """Skeleton backend for Raspberry Pi using Blinka-compatible APIs."""

    def __init__(self) -> None:
        self._input_cache: dict[str, bool] = {}
        self._output_cache: dict[str, bool] = {}

    def read(self, address: str) -> bool:
        return bool(self._input_cache.get(address, False))

    def write(self, address: str, value: bool) -> None:
        self._output_cache[address] = bool(value)
