import ctypes as C
from .abi import *
from .discovery import discover_library
from .errors import NativeAbiMismatchError,NativeLibraryLoadError,RSmicroNativeError

class NativeBinding:
 def __init__(self,path=None):
  search=discover_library(path); self.path=search.selected; self.search=search
  try: self.lib=C.CDLL(self.path)
  except OSError as e: raise NativeLibraryLoadError(str(e),library_path=self.path) from e
  self._declare()
  actual=(self.lib.rsm_runtime_abi_major(),self.lib.rsm_runtime_abi_minor())
  if actual[0]!=1 or self.lib.rsm_instruction_abi()!=1 or self.lib.rsm_image_format_major()!=1 or self.lib.rsm_profile_id()!=1: raise NativeAbiMismatchError(f"incompatible native ABI: runtime={actual}, instruction={self.lib.rsm_instruction_abi()}",library_path=self.path)
 def _declare(self):
  l=self.lib
  for n in ("rsm_runtime_abi_major","rsm_runtime_abi_minor","rsm_instruction_abi","rsm_image_format_major","rsm_image_format_minor","rsm_profile_id"): getattr(l,n).restype=C.c_uint32
  l.rsm_runtime_object_size.restype=C.c_size_t
  for n in ("rsm_status_name","rsm_mode_name","rsm_type_name","rsm_fault_category_name"): getattr(l,n).restype=C.c_char_p
  l.rsm_runtime_validate_image.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(ImageInfo)]; l.rsm_runtime_validate_image.restype=C.c_int
  l.rsm_runtime_required_memory.argtypes=[C.POINTER(C.c_uint8),C.c_size_t,C.POINTER(C.c_size_t)]; l.rsm_runtime_required_memory.restype=C.c_int
  l.rsm_runtime_init.argtypes=[C.c_void_p,C.c_void_p,C.c_size_t,C.POINTER(Hal),C.c_void_p]; l.rsm_runtime_init.restype=C.c_int
  for n,args in {"rsm_runtime_deinit":[C.c_void_p],"rsm_runtime_unload_program":[C.c_void_p],"rsm_runtime_scan":[C.c_void_p],"rsm_runtime_clear_all_forces":[C.c_void_p]}.items(): getattr(l,n).argtypes=args
  l.rsm_runtime_load_image.argtypes=[C.c_void_p,C.POINTER(C.c_uint8),C.c_size_t]; l.rsm_runtime_load_image.restype=C.c_int
  l.rsm_runtime_set_mode.argtypes=[C.c_void_p,C.c_int]; l.rsm_runtime_set_mode.restype=C.c_int; l.rsm_runtime_get_mode.argtypes=[C.c_void_p]; l.rsm_runtime_get_mode.restype=C.c_int
  for n in ("rsm_runtime_read_tag","rsm_runtime_write_tag","rsm_runtime_force_tag"): getattr(l,n).argtypes=[C.c_void_p,C.c_uint32,C.POINTER(Value)]; getattr(l,n).restype=C.c_int
  l.rsm_runtime_read_member.argtypes=[C.c_void_p,C.c_uint32,C.c_uint8,C.POINTER(Value)]; l.rsm_runtime_read_member.restype=C.c_int
  l.rsm_runtime_clear_force.argtypes=[C.c_void_p,C.c_uint32]; l.rsm_runtime_clear_force.restype=C.c_int
  l.rsm_runtime_snapshot.argtypes=[C.c_void_p,C.POINTER(SnapshotWriter)]; l.rsm_runtime_snapshot.restype=C.c_int
  l.rsm_runtime_get_diagnostics.argtypes=[C.c_void_p,C.POINTER(Diagnostics)]; l.rsm_runtime_get_diagnostics.restype=C.c_int
  l.rsm_runtime_last_fault.argtypes=[C.c_void_p]; l.rsm_runtime_last_fault.restype=C.POINTER(Fault)
 def check(self,status,operation):
  if status:
   name=self.lib.rsm_status_name(status).decode(); raise RSmicroNativeError(f"{operation} failed: {name} ({status})",operation=operation,status=status,status_name=name,library_path=self.path)
