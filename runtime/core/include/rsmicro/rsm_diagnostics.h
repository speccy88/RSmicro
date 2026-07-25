#ifndef RSM_DIAGNOSTICS_H
#define RSM_DIAGNOSTICS_H
#include <stdint.h>
typedef struct { uint64_t scan_count,last_scan_start_us,last_scan_duration_us,average_scan_duration_us,max_scan_duration_us,overrun_count,fault_count; uint32_t active_force_count,tag_count,instruction_count,state_slot_count,last_instruction_id; } rsm_runtime_diagnostics_t;
#endif
