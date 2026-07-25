#ifndef RSM_FAULT_H
#define RSM_FAULT_H
#include <stdint.h>
typedef enum {RSM_FAULT_NONE,RSM_FAULT_IMAGE,RSM_FAULT_CONFIGURATION,RSM_FAULT_MEMORY,RSM_FAULT_EXECUTION,RSM_FAULT_NUMERIC,RSM_FAULT_TIMER,RSM_FAULT_COUNTER,RSM_FAULT_HAL,RSM_FAULT_WATCHDOG,RSM_FAULT_INTERNAL} rsm_fault_category_t;
typedef struct { rsm_fault_category_t category; uint32_t code; uint64_t scan_number,timestamp_us; uint32_t routine_id,rung_id,instruction_id,tag_id; uint8_t opcode,major; const char *message_id; } rsm_fault_t;
#endif
