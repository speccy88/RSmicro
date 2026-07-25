from __future__ import annotations
import threading,time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from .runtime import NativeRuntime,NativeSimulationHAL,RuntimeMode
from ..model import load_project
from ..compiler import compile_project
from .errors import NativeSimulationError

class SimulatorState(Enum): CREATED="CREATED"; COMPILED="COMPILED"; LOADED="LOADED"; PROGRAM="PROGRAM"; RUNNING="RUNNING"; TESTING="TESTING"; STOPPED="STOPPED"; FAULTED="FAULTED"; CLOSED="CLOSED"
@dataclass(frozen=True)
class SimulatorEvent: kind:str; state:SimulatorState; payload:object=None

class NativeSimulator:
 def __init__(self,runtime,scan_period_ms=10): self.runtime=runtime; self.hal=runtime.hal; self.scan_period=scan_period_ms/1000; self.state=SimulatorState.LOADED; self._subscribers=set(); self._stop=threading.Event(); self._worker=None; self.scheduler_overruns=0; self.worker_error=None; self.compiler_diagnostics=(); self._lock=threading.RLock()
 @classmethod
 def from_project(cls,project_path,controller,deployment=None,library=None,scan_period_ms=10):
  p=load_project(project_path); result=compile_project(p,controller,deployment_id=deployment)
  if not result.success: raise NativeSimulationError("compilation failed: "+"; ".join(f"{x.code}: {x.message}" for x in result.diagnostics))
  rt=NativeRuntime(library,NativeSimulationHAL()).load_image(result.image_bytes,result.manifest,result.debug_map); obj=cls(rt,scan_period_ms); obj.compiler_diagnostics=tuple(result.diagnostics); obj.state=SimulatorState.PROGRAM; return obj
 def subscribe(self,callback): self._subscribers.add(callback); return lambda:self._subscribers.discard(callback)
 def _emit(self,kind,payload=None):
  event=SimulatorEvent(kind,self.state,payload)
  for cb in tuple(self._subscribers):
   try: cb(event)
   except Exception: pass
 def set_mode(self,mode):
  with self._lock: self.runtime.set_mode(mode); self.state={RuntimeMode.PROGRAM:SimulatorState.PROGRAM,RuntimeMode.RUN:SimulatorState.RUNNING,RuntimeMode.TEST:SimulatorState.TESTING}[RuntimeMode(mode)]
  self._emit("MODE_CHANGED",self.runtime.mode)
 def scan(self):
  with self._lock: self.runtime.scan(); d=self.runtime.diagnostics()
  self._emit("SCAN_COMPLETED",d); return d
 def start(self):
  if self._worker and self._worker.is_alive(): return
  if self.runtime.mode not in (RuntimeMode.RUN,RuntimeMode.TEST): self.set_mode(RuntimeMode.RUN)
  self._stop.clear(); self._worker=threading.Thread(target=self._loop,name="rsmicro-native-scan",daemon=True); self._worker.start()
 def _loop(self):
  deadline=time.monotonic()
  try:
   while not self._stop.is_set():
    deadline+=self.scan_period; self.scan(); delay=deadline-time.monotonic()
    if delay<0:self.scheduler_overruns+=1; deadline=time.monotonic()
    else:self._stop.wait(delay)
  except Exception as e: self.worker_error=e; self.state=SimulatorState.FAULTED; self._stop.set(); self._emit("FAULTED",self.runtime.last_fault())
 def stop(self):
  self._stop.set()
  if self._worker and self._worker is not threading.current_thread(): self._worker.join(5)
  if self.runtime.mode in (RuntimeMode.RUN,RuntimeMode.TEST): self.set_mode(RuntimeMode.PROGRAM)
  self.state=SimulatorState.STOPPED; self._emit("STOPPED")
 def close(self): self.stop(); self.runtime.close(); self.state=SimulatorState.CLOSED
