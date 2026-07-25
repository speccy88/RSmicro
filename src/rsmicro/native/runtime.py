from __future__ import annotations

import ctypes as C
import hashlib
import threading
import time
from dataclasses import asdict, dataclass
from enum import IntEnum
from pathlib import Path

from .abi import *
from .binding import NativeBinding
from .errors import NativeImageError, NativeTagError, RSmicroNativeError
from .values import BoolValue, CounterValue, DintValue, RealValue, TimerValue, normalize


class RuntimeMode(IntEnum):
    PROGRAM = 0
    RUN = 1
    TEST = 2
    FAULTED = 3


class NativeSimulationHAL:
    def __init__(self, manual=True):
        self.manual = manual
        self._time_us = 0
        self.inputs, self.outputs, self.safe_outputs = {}, {}, {}
        self.read_count = self.write_count = self.watchdog_count = 0
        self.fail_reads, self.fail_writes, self.fail_watchdog = set(), set(), False
        self._callbacks = (TIME_CB(self._time), READ_CB(self._read), WRITE_CB(self._write),
                           WATCHDOG_CB(self._watchdog), EVENT_CB(self._event))
        self.struct = Hal(*self._callbacks)

    def now_us(self): return self._time_us if self.manual else time.monotonic_ns() // 1000
    def set_time_us(self, value):
        if not self.manual: raise RuntimeError("manual time is disabled")
        if value < self._time_us: raise ValueError("monotonic time cannot move backwards")
        self._time_us = int(value)
    def advance_time_us(self, value): self.set_time_us(self._time_us + int(value))
    def set_input(self, endpoint, value, type_name): self.inputs[int(endpoint)] = normalize(value, type_name)
    def _time(self, _): return self.now_us()
    def _read(self, _, endpoint, out):
        self.read_count += 1
        if endpoint in self.fail_reads or endpoint not in self.inputs: return 16
        _to_c(self.inputs[endpoint], out.contents); return 0
    def _write(self, _, endpoint, value):
        self.write_count += 1
        if endpoint in self.fail_writes: return 16
        self.outputs[endpoint] = _from_c(value.contents); return 0
    def _watchdog(self, _): self.watchdog_count += 1; return 16 if self.fail_watchdog else 0
    def _event(self, *_): pass


@dataclass(frozen=True)
class RuntimeDiagnostics:
    scan_count: int; last_scan_start_us: int; last_scan_duration_us: int
    average_scan_duration_us: int; max_scan_duration_us: int; overrun_count: int
    fault_count: int; active_force_count: int; tag_count: int; instruction_count: int
    state_slot_count: int; last_instruction_id: int
    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class RuntimeFault:
    category: str; code: int; scan_number: int; timestamp_us: int
    instruction_id: int; tag_id: int; opcode: int; major: bool; message_id: str


@dataclass(frozen=True)
class SnapshotValue:
    runtime_id: int; logical: object; effective: object; forced: bool


@dataclass(frozen=True)
class SnapshotMember:
    runtime_id: int; member: int; value: object


@dataclass(frozen=True)
class SnapshotInstructionState:
    slot: int; edge: bool; valid: bool; timestamp_us: int


@dataclass(frozen=True)
class SnapshotRungPower:
    rung_id: int; powered: bool


@dataclass(frozen=True)
class WriteTrace:
    runtime_id: int; value: object


@dataclass(frozen=True)
class RuntimeSnapshot:
    mode: RuntimeMode; scan_count: int; program_hash: str | None
    values: tuple[SnapshotValue, ...]; members: tuple[SnapshotMember, ...]
    instruction_states: tuple[SnapshotInstructionState, ...]
    rung_powers: tuple[SnapshotRungPower, ...]
    diagnostics: RuntimeDiagnostics; last_fault: RuntimeFault | None


def _to_c(v, out):
    if isinstance(v, BoolValue): out.type, out.value.boolean = 1, v.value
    elif isinstance(v, DintValue): out.type, out.value.dint = 2, v.value
    elif isinstance(v, RealValue): out.type, out.value.real = 3, v.value
    else: raise TypeError("composite values cannot be written")


def _from_c(v):
    return (BoolValue(bool(v.value.boolean)) if v.type == 1 else
            DintValue(v.value.dint) if v.type == 2 else
            RealValue(float(v.value.real)) if v.type == 3 else None)


def _diagnostics_from_c(d):
    return RuntimeDiagnostics(
        d.scan_count, d.last_scan_start_us, d.last_scan_duration_us,
        d.average_scan_duration_us, d.max_scan_duration_us, d.overrun_count,
        d.fault_count, d.active_force_count, d.tag_count, d.instruction_count,
        d.state_slot_count, d.last_instruction_id)


class NativeRuntime:
    """Thread-safe owner of one native runtime object and its caller-owned arena."""
    def __init__(self, library=None, hal=None):
        self.binding = NativeBinding(library)
        self.hal = hal or NativeSimulationHAL()
        self._object = C.create_string_buffer(self.binding.lib.rsm_runtime_object_size())
        self._arena = self._image = self._map = self._manifest = None
        self._program_hash = None
        self._initialized = self._program_loaded = self._closed = False
        self._lock = threading.RLock()

    def __enter__(self): return self
    def __exit__(self, *_): self.close()

    def _open(self):
        if self._closed: raise RSmicroNativeError("native runtime is closed")

    def _require_program(self):
        if not self._program_loaded:
            raise RSmicroNativeError("native runtime has no loaded program", operation="runtime operation",
                                     status=2, status_name="INVALID_STATE", library_path=self.binding.path)

    def _clear_program_metadata(self):
        self._image = self._map = self._manifest = self._program_hash = None
        self._program_loaded = False

    @property
    def program_hash(self):
        with self._lock:
            self._open()
            return self._program_hash

    def validate_image(self, data):
        with self._lock:
            self._open()
            buf = (C.c_uint8 * len(data)).from_buffer_copy(data)
            info = ImageInfo()
            self.binding.check(self.binding.lib.rsm_runtime_validate_image(buf, len(data), C.byref(info)), "validate image")
            return info

    def load_image(self, image, manifest=None, debug_map=None):
        with self._lock:
            self._open()
            data = Path(image).read_bytes() if isinstance(image, (str, Path)) else bytes(image)
            self.validate_image(data)
            digest = hashlib.sha256(data).hexdigest()
            if manifest and manifest.get("image_sha256") != digest:
                raise NativeImageError("manifest image hash does not match image")
            native_image = (C.c_uint8 * len(data)).from_buffer_copy(data)
            if not self._initialized:
                need = C.c_size_t()
                self.binding.check(self.binding.lib.rsm_runtime_required_memory(native_image, len(data), C.byref(need)), "required memory")
                self._arena = C.create_string_buffer(need.value + 8)
                self.binding.check(self.binding.lib.rsm_runtime_init(self._object, self._arena, len(self._arena), C.byref(self.hal.struct), None), "initialize runtime")
                self._initialized = True
            self.binding.check(self.binding.lib.rsm_runtime_load_image(self._object, native_image, len(data)), "load image")
            self._image, self._manifest, self._map, self._program_hash = native_image, manifest, debug_map, digest
            self._program_loaded = True
            return self

    @classmethod
    def from_image(cls, image, **kw): return cls(**kw).load_image(image)

    def close(self):
        with self._lock:
            if not self._closed:
                if self._initialized: self.binding.lib.rsm_runtime_deinit(self._object)
                self._initialized = False
                self._arena = None
                self._clear_program_metadata()
                self._closed = True

    def unload(self):
        with self._lock:
            self._open()
            self.binding.check(self.binding.lib.rsm_runtime_unload_program(self._object), "unload program")
            self._clear_program_metadata()

    @property
    def mode(self):
        with self._lock:
            self._open()
            return RuntimeMode(self.binding.lib.rsm_runtime_get_mode(self._object))

    def set_mode(self, mode):
        with self._lock:
            self._open(); self._require_program()
            self.binding.check(self.binding.lib.rsm_runtime_set_mode(self._object, int(RuntimeMode(mode))), "set mode")

    def prescan(self):
        with self._lock:
            self._open(); self._require_program(); self.binding.check(self.binding.lib.rsm_runtime_prescan(self._object), "prescan")

    def postscan(self):
        with self._lock:
            self._open(); self._require_program(); self.binding.check(self.binding.lib.rsm_runtime_postscan(self._object), "postscan")

    def scan(self):
        with self._lock:
            self._open(); self._require_program(); self.binding.check(self.binding.lib.rsm_runtime_scan(self._object), "scan")

    def _id(self, key):
        if isinstance(key, int): return key
        if not self._map: raise NativeTagError("UUID/name access requires a matching debug map")
        hits = [x for x in self._map["tags"] if x["uuid"] == key or x["name"] == key]
        if len(hits) != 1:
            raise NativeTagError(f"tag name/UUID is {'ambiguous: ' + ', '.join(x['uuid'] for x in hits) if hits else 'not found'}")
        return hits[0]["runtime_id"]

    def _type(self, key):
        rid = self._id(key)
        if not self._map: raise NativeTagError("typed writes require a debug map")
        return next(x["type"] for x in self._map["tags"] if x["runtime_id"] == rid)

    def read_tag(self, key):
        with self._lock:
            self._open(); self._require_program()
            rid, typ = self._id(key), self._type(key) if self._map else None
            if typ in ("TIMER", "COUNTER"):
                names = ("PRE", "ACC", "EN", "TT", "DN") if typ == "TIMER" else ("PRE", "ACC", None, None, "DN", "CU", "CD", "OV", "UN")
                vals = [self.read_member(rid, name) for name in names if name]
                return (TimerValue(vals[0].value, vals[1].value, *(x.value for x in vals[2:])) if typ == "TIMER" else
                        CounterValue(vals[0].value, vals[1].value, vals[3].value, vals[4].value, vals[2].value, vals[5].value, vals[6].value))
            value = Value(); self.binding.check(self.binding.lib.rsm_runtime_read_tag(self._object, rid, C.byref(value)), "read tag")
            return _from_c(value)

    def read_member(self, key, member):
        with self._lock:
            self._open(); self._require_program()
            ids = {"PRE": 1, "ACC": 2, "EN": 3, "TT": 4, "DN": 5, "CU": 6, "CD": 7, "OV": 8, "UN": 9}
            value = Value()
            self.binding.check(self.binding.lib.rsm_runtime_read_member(self._object, self._id(key), ids.get(str(member).upper(), member), C.byref(value)), "read member")
            return _from_c(value)

    def _change(self, fn, key, value):
        rid = self._id(key); native_value = Value()
        _to_c(normalize(value, self._type(rid)), native_value)
        self.binding.check(fn(self._object, rid, C.byref(native_value)), "change tag")

    def write_tag(self, key, value):
        with self._lock: self._open(); self._require_program(); self._change(self.binding.lib.rsm_runtime_write_tag, key, value)
    def force_tag(self, key, value):
        with self._lock: self._open(); self._require_program(); self._change(self.binding.lib.rsm_runtime_force_tag, key, value)
    def clear_force(self, key):
        with self._lock: self._open(); self._require_program(); self.binding.check(self.binding.lib.rsm_runtime_clear_force(self._object, self._id(key)), "clear force")
    def clear_all_forces(self):
        with self._lock: self._open(); self._require_program(); self.binding.check(self.binding.lib.rsm_runtime_clear_all_forces(self._object), "clear all forces")

    def clear_write_trace(self):
        with self._lock: self._open(); self._require_program(); self.binding.check(self.binding.lib.rsm_runtime_clear_write_trace(self._object), "clear write trace")

    def get_write_trace(self):
        with self._lock:
            self._open(); self._require_program()
            entries = (WriteTraceEntry * 64)(); count = C.c_size_t()
            self.binding.check(self.binding.lib.rsm_runtime_get_write_trace(self._object, entries, len(entries), C.byref(count)), "get write trace")
            return tuple(WriteTrace(entry.tag, _from_c(entries[index].value)) for index, entry in enumerate(entries[:count.value]))

    def diagnostics(self):
        with self._lock:
            self._open(); self._require_program(); d = Diagnostics()
            self.binding.check(self.binding.lib.rsm_runtime_get_diagnostics(self._object, C.byref(d)), "diagnostics")
            return _diagnostics_from_c(d)

    def last_fault(self):
        with self._lock:
            self._open(); self._require_program(); pointer = self.binding.lib.rsm_runtime_last_fault(self._object)
            if not pointer or pointer.contents.category == 0: return None
            f = pointer.contents
            return RuntimeFault(self.binding.lib.rsm_fault_category_name(f.category).decode(), f.code, f.scan_number, f.timestamp_us, f.instruction_id, f.tag_id, f.opcode, bool(f.major), (f.message_id or b"").decode())

    def snapshot(self):
        with self._lock:
            self._open(); self._require_program()
            values, members, states, rungs = [], [], [], []
            snapshot_mode = None
            snapshot_diagnostics = None
            snapshot_fault = None
            @SNAPSHOT_CB
            def value_cb(_, rid, logical, effective, forced):
                values.append(SnapshotValue(rid, _from_c(logical.contents), _from_c(effective.contents), bool(forced))); return 0
            @SNAPSHOT_MEMBER_CB
            def member_cb(_, rid, member, value):
                members.append(SnapshotMember(rid, member, _from_c(value.contents))); return 0
            @SNAPSHOT_STATE_CB
            def state_cb(_, mode, diagnostics, fault, slot, edge, valid, timestamp):
                nonlocal snapshot_mode, snapshot_diagnostics, snapshot_fault
                snapshot_mode = RuntimeMode(mode)
                snapshot_diagnostics = _diagnostics_from_c(diagnostics.contents)
                snapshot_fault = self._fault_from_c(fault.contents) if fault and fault.contents.category else None
                if slot != 0xffffffff: states.append(SnapshotInstructionState(slot, bool(edge), bool(valid), timestamp))
                return 0
            @SNAPSHOT_RUNG_CB
            def rung_cb(_, rung_id, powered): rungs.append(SnapshotRungPower(rung_id, bool(powered))); return 0
            writer = SnapshotWriter(None, value_cb, member_cb, state_cb, rung_cb)
            self.binding.check(self.binding.lib.rsm_runtime_snapshot(self._object, C.byref(writer)), "snapshot")
            # Keep writer/callbacks and callback-owned lists alive until this native call returns.
            diagnostics = snapshot_diagnostics or self.diagnostics()
            mode = snapshot_mode if snapshot_mode is not None else self.mode
            return RuntimeSnapshot(mode, diagnostics.scan_count, self._program_hash,
                                   tuple(values), tuple(members), tuple(states), tuple(rungs),
                                   diagnostics, snapshot_fault)

    def _fault_from_c(self, f):
        return RuntimeFault(self.binding.lib.rsm_fault_category_name(f.category).decode(), f.code, f.scan_number, f.timestamp_us, f.instruction_id, f.tag_id, f.opcode, bool(f.major), (f.message_id or b"").decode())
