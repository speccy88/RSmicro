#ifndef RSM_SNAPSHOT_H
#define RSM_SNAPSHOT_H
#include "rsm_types.h"
#include "rsm_status.h"
#include "rsm_diagnostics.h"
#include "rsm_fault.h"
/* A snapshot is deliberately observational: callbacks receive copies and never
 * invoke HAL or mutate scan/instruction state.  One writer covers scalar and
 * composite values plus the runtime envelope, so consumers cannot accidentally
 * omit composite or lifecycle state. */
typedef rsm_status_t (*rsm_snapshot_value_fn)(void *,rsm_tag_id_t,const rsm_value_t *,const rsm_value_t *,rsm_bool_t);
typedef rsm_status_t (*rsm_snapshot_member_fn)(void *,rsm_tag_id_t,rsm_member_id_t,const rsm_value_t *);
typedef rsm_status_t (*rsm_snapshot_state_fn)(void *,uint8_t,const rsm_runtime_diagnostics_t *,const rsm_fault_t *,uint32_t,uint8_t,uint8_t,uint64_t);
typedef rsm_status_t (*rsm_snapshot_rung_fn)(void *,uint32_t,rsm_bool_t);
typedef struct { void *context; rsm_snapshot_value_fn value; rsm_snapshot_member_fn member; rsm_snapshot_state_fn state; rsm_snapshot_rung_fn rung_power; } rsm_snapshot_writer_t;
typedef struct { void *context; rsm_snapshot_member_fn member; } rsm_snapshot_member_writer_t;
#endif
