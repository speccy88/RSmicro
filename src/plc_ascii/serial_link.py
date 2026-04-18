from __future__ import annotations

import queue
import time
from dataclasses import dataclass, field

from .protocol import decode_message, encode_message

try:
    import serial  # type: ignore
except ImportError:  # pragma: no cover
    serial = None


@dataclass
class SerialJsonTransport:
    port: str
    baudrate: int = 115200
    timeout: float = 0.1
    _serial: object | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed. Install with: pip install -e .[serial]")
        self._serial = serial.Serial(self.port, self.baudrate, timeout=self.timeout)

    def send(self, payload: dict) -> None:
        assert self._serial is not None
        self._serial.write(encode_message(payload))

    def recv(self, timeout: float | None = None) -> dict | None:
        assert self._serial is not None
        end_time = None if timeout is None else time.monotonic() + timeout
        while True:
            line = self._serial.readline()
            if line:
                return decode_message(line)
            if end_time is not None and time.monotonic() >= end_time:
                return None

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()


@dataclass
class QueueTransport:
    """A simple in-memory transport used for tests and local demos."""

    incoming: queue.Queue[dict] = field(default_factory=queue.Queue)
    outgoing: queue.Queue[dict] = field(default_factory=queue.Queue)

    def send(self, payload: dict) -> None:
        self.outgoing.put(payload)

    def recv(self, timeout: float | None = None) -> dict | None:
        try:
            return self.incoming.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        return None
