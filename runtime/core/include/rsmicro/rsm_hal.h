#ifndef RSM_HAL_H
#define RSM_HAL_H
#include "rsm_status.h"
#include "rsm_types.h"
typedef struct { uint64_t (*monotonic_time_us)(void *); rsm_status_t (*read_input)(void *,uint32_t,rsm_value_t *); rsm_status_t (*write_output)(void *,uint32_t,const rsm_value_t *); rsm_status_t (*kick_watchdog)(void *); void (*log_event)(void *,uint32_t,int32_t); } rsm_hal_t;
#endif
