import ctypes as C

from .abi import *
from .discovery import discover_library
from .errors import NativeAbiMismatchError, NativeLibraryLoadError, RSmicroNativeError


class NativeBinding:
    def __init__(self, path=None):
        search = discover_library(path)
        self.path, self.search = search.selected, search
        try:
            self.lib = C.CDLL(self.path)
        except OSError as exc:
            raise NativeLibraryLoadError(str(exc), library_path=self.path) from exc
        self._declare()
        actual = (self.lib.rsm_runtime_abi_major(), self.lib.rsm_runtime_abi_minor())
        if (actual != RUNTIME_ABI or
                self.lib.rsm_instruction_abi() != 2 or
                self.lib.rsm_image_format_major() != 2 or
                self.lib.rsm_profile_id() != 1):
            raise NativeAbiMismatchError(
                f"incompatible native ABI: runtime={actual}, "
                f"instruction={self.lib.rsm_instruction_abi()}", library_path=self.path)

    def _declare(self):
        l = self.lib
        for name in ("rsm_runtime_abi_major", "rsm_runtime_abi_minor",
                     "rsm_instruction_abi", "rsm_image_format_major",
                     "rsm_image_format_minor", "rsm_profile_id"):
            fn = getattr(l, name)
            fn.argtypes, fn.restype = [], C.c_uint32
        l.rsm_runtime_object_size.argtypes, l.rsm_runtime_object_size.restype = [], C.c_size_t
        for name, argument in (("rsm_status_name", C.c_int), ("rsm_mode_name", C.c_int),
                               ("rsm_type_name", C.c_int),
                               ("rsm_fault_category_name", C.c_int)):
            fn = getattr(l, name)
            fn.argtypes, fn.restype = [argument], C.c_char_p
        l.rsm_runtime_validate_image.argtypes = [C.POINTER(C.c_uint8), C.c_size_t, C.POINTER(ImageInfo)]
        l.rsm_runtime_validate_image.restype = C.c_int
        l.rsm_runtime_required_memory.argtypes = [C.POINTER(C.c_uint8), C.c_size_t, C.POINTER(C.c_size_t)]
        l.rsm_runtime_required_memory.restype = C.c_int
        l.rsm_runtime_init.argtypes = [C.c_void_p, C.c_void_p, C.c_size_t, C.POINTER(Hal), C.c_void_p]
        l.rsm_runtime_init.restype = C.c_int
        l.rsm_runtime_deinit.argtypes, l.rsm_runtime_deinit.restype = [C.c_void_p], None
        for name in ("rsm_runtime_unload_program", "rsm_runtime_prescan",
                     "rsm_runtime_postscan", "rsm_runtime_scan",
                     "rsm_runtime_clear_all_forces", "rsm_runtime_clear_write_trace"):
            fn = getattr(l, name)
            fn.argtypes, fn.restype = [C.c_void_p], C.c_int
        l.rsm_runtime_load_image.argtypes = [C.c_void_p, C.POINTER(C.c_uint8), C.c_size_t]
        l.rsm_runtime_load_image.restype = C.c_int
        l.rsm_runtime_set_mode.argtypes, l.rsm_runtime_set_mode.restype = [C.c_void_p, C.c_int], C.c_int
        l.rsm_runtime_get_mode.argtypes, l.rsm_runtime_get_mode.restype = [C.c_void_p], C.c_int
        for name in ("rsm_runtime_read_tag", "rsm_runtime_write_tag", "rsm_runtime_force_tag"):
            fn = getattr(l, name)
            fn.argtypes, fn.restype = [C.c_void_p, C.c_uint32, C.POINTER(Value)], C.c_int
        l.rsm_runtime_read_member.argtypes = [C.c_void_p, C.c_uint32, C.c_uint8, C.POINTER(Value)]
        l.rsm_runtime_read_member.restype = C.c_int
        l.rsm_runtime_clear_force.argtypes, l.rsm_runtime_clear_force.restype = [C.c_void_p, C.c_uint32], C.c_int
        l.rsm_runtime_get_write_trace.argtypes = [C.c_void_p, C.POINTER(WriteTraceEntry), C.c_size_t, C.POINTER(C.c_size_t)]
        l.rsm_runtime_get_write_trace.restype = C.c_int
        l.rsm_runtime_snapshot.argtypes, l.rsm_runtime_snapshot.restype = [C.c_void_p, C.POINTER(SnapshotWriter)], C.c_int
        l.rsm_runtime_snapshot_members.argtypes, l.rsm_runtime_snapshot_members.restype = [C.c_void_p, C.POINTER(SnapshotMemberWriter)], C.c_int
        l.rsm_runtime_get_diagnostics.argtypes, l.rsm_runtime_get_diagnostics.restype = [C.c_void_p, C.POINTER(Diagnostics)], C.c_int
        l.rsm_runtime_last_fault.argtypes, l.rsm_runtime_last_fault.restype = [C.c_void_p], C.POINTER(Fault)

    def check(self, status, operation):
        if status:
            name = self.lib.rsm_status_name(status).decode()
            raise RSmicroNativeError(f"{operation} failed: {name} ({status})",
                                     operation=operation, status=status,
                                     status_name=name, library_path=self.path)
