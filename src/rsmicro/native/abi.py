import ctypes as C

class ValueUnion(C.Union): _fields_=[("boolean",C.c_uint8),("dint",C.c_int32),("real",C.c_float)]
class Value(C.Structure): _fields_=[("type",C.c_int),("value",ValueUnion)]
TIME_CB=C.CFUNCTYPE(C.c_uint64,C.c_void_p)
READ_CB=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_uint32,C.POINTER(Value))
WRITE_CB=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_uint32,C.POINTER(Value))
WATCHDOG_CB=C.CFUNCTYPE(C.c_int,C.c_void_p)
EVENT_CB=C.CFUNCTYPE(None,C.c_void_p,C.c_uint32,C.c_int32)
class Hal(C.Structure): _fields_=[("monotonic_time_us",TIME_CB),("read_input",READ_CB),("write_output",WRITE_CB),("kick_watchdog",WATCHDOG_CB),("log_event",EVENT_CB)]
class Diagnostics(C.Structure): _fields_=[(x,C.c_uint64) for x in ("scan_count","last_scan_start_us","last_scan_duration_us","average_scan_duration_us","max_scan_duration_us","overrun_count","fault_count")]+[(x,C.c_uint32) for x in ("active_force_count","tag_count","instruction_count","state_slot_count","last_instruction_id")]
class Fault(C.Structure): _fields_=[("category",C.c_int),("code",C.c_uint32),("scan_number",C.c_uint64),("timestamp_us",C.c_uint64),("routine_id",C.c_uint32),("rung_id",C.c_uint32),("instruction_id",C.c_uint32),("tag_id",C.c_uint32),("opcode",C.c_uint8),("major",C.c_uint8),("message_id",C.c_char_p)]
SNAPSHOT_CB=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_uint32,C.POINTER(Value),C.POINTER(Value),C.c_uint8)
SNAPSHOT_MEMBER_CB=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_uint32,C.c_uint8,C.POINTER(Value))
SNAPSHOT_STATE_CB=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_uint8,C.POINTER(Diagnostics),C.POINTER(Fault),C.c_uint32,C.c_uint8,C.c_uint8,C.c_uint64)
SNAPSHOT_RUNG_CB=C.CFUNCTYPE(C.c_int,C.c_void_p,C.c_uint32,C.c_uint8)
class SnapshotWriter(C.Structure): _fields_=[("context",C.c_void_p),("value",SNAPSHOT_CB),("member",SNAPSHOT_MEMBER_CB),("state",SNAPSHOT_STATE_CB),("rung_power",SNAPSHOT_RUNG_CB)]
class SnapshotMemberWriter(C.Structure): _fields_=[("context",C.c_void_p),("member",SNAPSHOT_MEMBER_CB)]
class ImageInfo(C.Structure): _fields_=[("major",C.c_uint8),("minor",C.c_uint8),("profile_id",C.c_uint16),("instruction_abi",C.c_uint16),("section_count",C.c_uint16),("image_size",C.c_uint32),("tag_count",C.c_uint32),("instruction_count",C.c_uint32)]
