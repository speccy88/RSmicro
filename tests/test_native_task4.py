import ctypes as C
import threading
from pathlib import Path

import pytest

from rsmicro.compiler import compile_project
from rsmicro.model import load_project
from rsmicro.native import (DintValue, NativeBinding, NativeRuntime, NativeSimulator,
                            RealValue, RuntimeMode)
from rsmicro.native.abi import ImageInfo, Value, WriteTraceEntry
from rsmicro.native.errors import NativeImageError, RSmicroNativeError
from rsmicro.native.simulation import SimulatorEvent

ROOT = Path(__file__).parents[1]


@pytest.fixture
def compiled():
    project = load_project(ROOT / "examples/native_core_demo/project.rsmproj")
    result = compile_project(project, project.controllers[0].controller_id)
    assert result.success
    return result


def test_binding_versions_and_abi_declarations():
    binding = NativeBinding()  # discovery, never a platform-specific filename
    assert binding.lib.rsm_runtime_abi_major() == 1
    assert binding.lib.rsm_runtime_abi_minor() == 2
    assert binding.lib.rsm_instruction_abi() == 2
    assert binding.lib.rsm_runtime_deinit.argtypes == [C.c_void_p]
    assert binding.lib.rsm_runtime_deinit.restype is None
    assert binding.lib.rsm_runtime_get_write_trace.argtypes == [
        C.c_void_p, C.POINTER(WriteTraceEntry), C.c_size_t, C.POINTER(C.c_size_t)]
    assert C.sizeof(WriteTraceEntry) == C.sizeof(C.c_uint32) + C.sizeof(Value)


def test_image_info_ctypes_layout_matches_native_c_abi():
    """Guard the output struct passed to ``rsm_runtime_validate_image``.

    ``rsm_image_info_t`` is a packed-by-natural-alignment C structure with
    four trailing uint32 fields.  Omitting one makes C write past ctypes'
    allocated object when it fills the validation result.
    """
    assert C.sizeof(ImageInfo) == 24
    assert (ImageInfo.major.offset, ImageInfo.minor.offset,
            ImageInfo.profile_id.offset, ImageInfo.instruction_abi.offset,
            ImageInfo.section_count.offset, ImageInfo.image_size.offset,
            ImageInfo.tag_count.offset, ImageInfo.instruction_count.offset,
            ImageInfo.rung_count.offset) == (0, 1, 2, 4, 6, 8, 12, 16, 20)


def test_runtime_lifecycle_values_complete_snapshot_and_scan_phases(compiled):
    with NativeRuntime().load_image(compiled.image_bytes, compiled.manifest, compiled.debug_map) as runtime:
        assert runtime.mode == RuntimeMode.PROGRAM
        assert runtime.read_tag("Count") == DintValue(1)
        assert runtime.read_tag("Gain") == RealValue(1.5)
        runtime.prescan(); runtime.postscan()
        runtime.write_tag("Count", 4); runtime.set_mode(RuntimeMode.RUN); runtime.scan()
        before = runtime.diagnostics(); snapshot = runtime.snapshot()
        assert snapshot.scan_count == before.scan_count == 1
        assert snapshot.diagnostics == before
        assert snapshot.members  # TIMER and COUNTER members arrive in the main traversal
        assert snapshot.instruction_states
        assert snapshot.rung_powers
        assert runtime.diagnostics().scan_count == 1  # snapshot is non-mutating
    with pytest.raises(RSmicroNativeError):
        _ = runtime.mode


def test_trace_records_logical_writes_and_clear(compiled):
    runtime = NativeRuntime().load_image(compiled.image_bytes, compiled.manifest, compiled.debug_map)
    runtime.clear_write_trace()
    runtime.force_tag("Count", 99)
    runtime.write_tag("Count", 7)
    assert runtime.read_tag("Count") == DintValue(99)
    trace = runtime.get_write_trace()
    assert trace and trace[-1].value == DintValue(7)
    runtime.clear_write_trace()
    assert runtime.get_write_trace() == ()
    runtime.close()


def test_unload_requires_program_mode_invalidates_and_reloads(compiled):
    runtime = NativeRuntime().load_image(compiled.image_bytes, compiled.manifest, compiled.debug_map)
    runtime.set_mode(RuntimeMode.RUN)
    with pytest.raises(RSmicroNativeError):
        runtime.unload()
    runtime.set_mode(RuntimeMode.PROGRAM)
    runtime.unload()
    assert runtime.program_hash is None
    with pytest.raises(RSmicroNativeError) as exc:
        runtime.scan()
    assert exc.value.status_name == "INVALID_STATE"
    runtime.load_image(compiled.image_bytes, compiled.manifest, compiled.debug_map)
    assert runtime.read_tag("Count") == DintValue(1)
    runtime.close()


def test_hash_two_instances_and_concurrent_public_operations(compiled):
    bad = dict(compiled.manifest, image_sha256="0" * 64)
    with pytest.raises(NativeImageError):
        NativeRuntime().load_image(compiled.image_bytes, bad, compiled.debug_map)
    first = NativeRuntime().load_image(compiled.image_bytes, compiled.manifest, compiled.debug_map)
    second = NativeRuntime().load_image(compiled.image_bytes, compiled.manifest, compiled.debug_map)
    first.write_tag("Count", 7)
    assert first.read_tag("Count") != second.read_tag("Count")
    simulator = NativeSimulator(first)
    simulator.set_mode(RuntimeMode.RUN)
    errors = []
    worker = threading.Thread(target=lambda: [simulator.scan() for _ in range(20)])
    worker.start()
    for _ in range(20):
        try:
            first.diagnostics(); first.snapshot(); first.get_write_trace()
        except Exception as error:  # direct calls and simulator calls share runtime lock
            errors.append(error)
    worker.join()
    assert not errors and simulator.worker_error is None
    simulator.close(); second.close()


def test_simulator_manual_and_events(compiled):
    runtime = NativeRuntime().load_image(compiled.image_bytes, compiled.manifest, compiled.debug_map)
    simulator = NativeSimulator(runtime); events: list[SimulatorEvent] = []
    simulator.subscribe(events.append); simulator.set_mode(RuntimeMode.RUN)
    simulator.scan(); simulator.hal.advance_time_us(500000); simulator.scan()
    assert [event.kind for event in events].count("SCAN_COMPLETED") == 2
    simulator.close()
