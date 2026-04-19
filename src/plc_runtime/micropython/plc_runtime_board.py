import json
import sys
import time

try:
    import select
except ImportError:  # pragma: no cover - on-device fallback
    import uselect as select

from machine import Pin

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

    def delete_program(self):
        try:
            import os

            os.remove(self.path)
        except OSError:
            return


class MicroPythonIOBackend:
    def __init__(self, config):
        self.config = config or {}
        self.pin_cache = {}
        self.pin_modes = {}
        self.input_overrides = {}

    def _normalized_address(self, address):
        if isinstance(address, int):
            return address
        text = str(address).strip()
        if not text:
            raise ValueError("Pin address cannot be empty")
        return int(text, 10)

    def _config_lookup(self, mapping, address):
        if address in mapping:
            return mapping[address]
        key = str(address)
        if key in mapping:
            return mapping[key]
        return None

    def _pin_object(self, address):
        pin_id = self._normalized_address(address)
        if pin_id not in self.pin_cache:
            self.pin_cache[pin_id] = Pin(pin_id)
        return self.pin_cache[pin_id], pin_id

    def _input_pull(self, address):
        pulls = self.config.get("input_pulls", {})
        value = self._config_lookup(pulls, self._normalized_address(address))
        if value == "up":
            return Pin.PULL_UP
        if value == "down":
            return Pin.PULL_DOWN
        return None

    def _active_low(self, address):
        active_low_inputs = self.config.get("active_low_inputs", [])
        pin_id = self._normalized_address(address)
        return pin_id in active_low_inputs or str(pin_id) in active_low_inputs

    def _configure(self, address, direction):
        pin, pin_id = self._pin_object(address)
        if self.pin_modes.get(pin_id) == direction:
            return pin, pin_id
        if direction == "input":
            pull = self._input_pull(pin_id)
            if pull is None:
                pin.init(mode=Pin.IN)
            else:
                pin.init(mode=Pin.IN, pull=pull)
        else:
            pin.init(mode=Pin.OUT)
        self.pin_modes[pin_id] = direction
        return pin, pin_id

    def read(self, address):
        pin_id = self._normalized_address(address)
        if pin_id in self.input_overrides:
            return self.input_overrides[pin_id]
        pin, _ = self._configure(pin_id, "input")
        value = bool(pin.value())
        if self._active_low(pin_id):
            value = not value
        return value

    def write(self, address, value):
        pin_id = self._normalized_address(address)
        if self._active_low(pin_id):
            self.input_overrides[pin_id] = bool(value)
            return
        pin, _ = self._configure(pin_id, "output")
        pin.value(1 if bool(value) else 0)


def load_config():
    try:
        with open(CONFIG_PATH, "r") as handle:
            return json.load(handle)
    except OSError:
        return {}
    except ValueError:
        return {}


def emit(payload):
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    if hasattr(sys.stdout, "flush"):
        sys.stdout.flush()


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
    backend = MicroPythonIOBackend(config)
    runtime = PortableRuntime(backend, JsonFileStorage(PROGRAM_PATH))
    runtime.mode = "run" if runtime.program_loaded else "stop"
    tick_period_ms = int(config.get("scan_ms", 50) or 50)
    last_tick = time.ticks_ms()
    buffer = ""
    poller = select.poll()
    poller.register(sys.stdin, select.POLLIN)

    while True:
        while poller.poll(0):
            chunk = sys.stdin.read(1)
            if not chunk:
                break
            buffer += chunk
            if chunk in ("\n", "\r"):
                buffer = buffer.replace("\r\n", "\n").replace("\r", "\n")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    process_line(runtime, line)

        now = time.ticks_ms()
        elapsed_ms = time.ticks_diff(now, last_tick)
        if elapsed_ms >= tick_period_ms:
            last_tick = now
            if runtime.mode == "run":
                runtime.scan_once(elapsed_ms)

        time.sleep_ms(10)
