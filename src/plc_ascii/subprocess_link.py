from __future__ import annotations

import json
import queue
import subprocess
import sys
import threading
from dataclasses import dataclass, field


@dataclass
class SubprocessJsonTransport:
    command: list[str] = field(default_factory=lambda: [sys.executable, "-m", "plc_runtime", "--demo"])
    _process: subprocess.Popen[str] | None = field(init=False, default=None)
    _incoming: queue.Queue[dict] = field(init=False, default_factory=queue.Queue)
    _reader: threading.Thread | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self._process = subprocess.Popen(
            self.command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self) -> None:
        assert self._process is not None
        assert self._process.stdout is not None
        for line in self._process.stdout:
            raw = line.strip()
            if not raw:
                continue
            self._incoming.put(json.loads(raw))

    def send(self, payload: dict) -> None:
        assert self._process is not None
        assert self._process.stdin is not None
        self._process.stdin.write(json.dumps(payload) + "\n")
        self._process.stdin.flush()

    def recv(self, timeout: float | None = None) -> dict | None:
        try:
            return self._incoming.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        if self._process is None:
            return
        self._process.terminate()
        self._process.wait(timeout=2)
