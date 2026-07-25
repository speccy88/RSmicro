from pathlib import Path
import pytest
from rsmicro.compiler import compile_project
from rsmicro.model import load_project
from rsmicro.native import NativeBinding,NativeRuntime,NativeSimulator,RuntimeMode,DintValue,RealValue
from rsmicro.native.errors import RSmicroNativeError,NativeImageError
ROOT=Path(__file__).parents[1]; LIB=ROOT/'build/runtime/core/librsmcore.so'
@pytest.fixture
def compiled():
 p=load_project(ROOT/'examples/native_core_demo/project.rsmproj'); r=compile_project(p,p.controllers[0].controller_id); assert r.success; return r
def test_binding_versions():
 b=NativeBinding(LIB); assert b.lib.rsm_runtime_abi_major()==1; assert b.lib.rsm_instruction_abi()==1
def test_runtime_lifecycle_values_snapshot(compiled):
 with NativeRuntime(LIB).load_image(compiled.image_bytes,compiled.manifest,compiled.debug_map) as r:
  assert r.mode==RuntimeMode.PROGRAM; assert r.read_tag('Count')==DintValue(1); assert r.read_tag('Gain')==RealValue(1.5)
  r.write_tag('Count',4); r.set_mode(RuntimeMode.RUN); r.scan(); before=r.diagnostics(); snap=r.snapshot(); assert snap.scan_count==before.scan_count==1; assert r.diagnostics().scan_count==1
 r.close()
 with pytest.raises(RSmicroNativeError): _=r.mode
def test_hash_and_multiple_instances(compiled):
 bad=dict(compiled.manifest,image_sha256='0'*64)
 with pytest.raises(NativeImageError): NativeRuntime(LIB).load_image(compiled.image_bytes,bad,compiled.debug_map)
 a=NativeRuntime(LIB).load_image(compiled.image_bytes,compiled.manifest,compiled.debug_map); b=NativeRuntime(LIB).load_image(compiled.image_bytes,compiled.manifest,compiled.debug_map)
 a.write_tag('Count',7); assert a.read_tag('Count')!=b.read_tag('Count'); a.close(); b.close()
def test_simulator_manual_and_events(compiled):
 r=NativeRuntime(LIB).load_image(compiled.image_bytes,compiled.manifest,compiled.debug_map); s=NativeSimulator(r); events=[]; s.subscribe(events.append); s.set_mode(RuntimeMode.RUN); s.scan(); s.hal.advance_time_us(500000); s.scan(); assert [e.kind for e in events].count('SCAN_COMPLETED')==2; s.close()
