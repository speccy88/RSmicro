import json
import time
import sys

import board
import supervisor
from digitalio import DigitalInOut, Direction, Pull

from plc_runtime_portable import PortableRuntime


PROGRAM_PATH = "plc_program.json"
CONFIG_PATH = "plc_runtime_config.json"


class JsonFileStorage:
    def __init__(self, path):
        self.path = path

    def load_program(self):
        try:
            with open(self.path, "r") as handle:
                return json.load(handle)
        except OSError:
            return None
        except ValueError:
            return None

    def save_program(self, program):
        with open(self.path, "w") as handle:
            json.dump(program, handle)


class CircuitPythonIOBackend:
    def __init__(self, config):
        self.config = config or {}
        self.pin_cache = {}
        self.pin_modes = {}
        self.input_overrides = {}

    def _pin_object(self, address):
        if address not in self.pin_cache:
            pin_name = str(address).strip()
            if not hasattr(board, pin_name):
                raise ValueError("Unknown board pin: " + pin_name)
            self.pin_cache[address] = DigitalInOut(getattr(board, pin_name))
        return self.pin_cache[address]

    def _input_pull(self, address):
        pulls = self.config.get("input_pulls", {})
        value = pulls.get(address)
        if value == "up":
            return Pull.UP
        if value == "down":
            return Pull.DOWN
        return None

    def _active_low(self, address):
        active_low_inputs = self.config.get("active_low_inputs", [])
        return address in active_low_inputs

    def _configure(self, address, direction):
        pin = self._pin_object(address)
        if self.pin_modes.get(address) == direction:
            return pin
        if direction == "input":
            pin.direction = Direction.INPUT
            pin.pull = self._input_pull(address)
        else:
            pin.direction = Direction.OUTPUT
        self.pin_modes[address] = direction
        return pin

    def read(self, address):
        if address in self.input_overrides:
            return self.input_overrides[address]
        pin = self._configure(address, "input")
        value = bool(pin.value)
        if self._active_low(address):
            value = not value
        return value

    def write(self, address, value):
        if address in self.config.get("active_low_inputs", []):
            self.input_overrides[address] = bool(value)
            return
        pin = self._configure(address, "output")
        pin.value = bool(value)


def load_config():
    try:
        with open(CONFIG_PATH, "r") as handle:
            return json.load(handle)
    except OSError:
        return {}
    except ValueError:
        return {}


def emit(payload):
    print(json.dumps(payload, separators=(",", ":")))


def process_line(runtime, raw):
    text = raw.strip()
    if not text:
        return
    try:
        payload = json.loads(text)
        response = runtime.handle_message(payload)
    except Exception as exc:
        response = {"type": "error", "message": str(exc)}
    emit(response)


def main():
    config = load_config()
    backend = CircuitPythonIOBackend(config)
    runtime = PortableRuntime(backend, JsonFileStorage(PROGRAM_PATH))
    runtime.mode = "run"
    tick_period_ms = int(config.get("scan_ms", 50) or 50)
    last_tick = time.monotonic()
    buffer = ""

    while True:
        if supervisor.runtime.serial_bytes_available:
            chunk = sys.stdin.read(supervisor.runtime.serial_bytes_available)
            if chunk:
                buffer += chunk
                buffer = buffer.replace("\r\n", "\n").replace("\r", "\n")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    process_line(runtime, line)

        now = time.monotonic()
        elapsed_ms = int((now - last_tick) * 1000)
        if elapsed_ms >= tick_period_ms:
            last_tick = now
            if runtime.mode == "run":
                runtime.scan_once(elapsed_ms)

        time.sleep(0.01)
