#ifndef RSM_RUNTIME_H
#define RSM_RUNTIME_H
#include <stddef.h>
#include "rsm_hal.h"
#include "rsm_image.h"
#include "rsm_fault.h"
#include "rsm_diagnostics.h"
#include "rsm_snapshot.h"
typedef enum {RSM_MODE_PROGRAM,RSM_MODE_RUN,RSM_MODE_TEST,RSM_MODE_FAULTED} rsm_mode_t;
typedef struct rsm_runtime { void *impl; void *arena; size_t arena_size; rsm_hal_t hal; void *hal_context; rsm_mode_t mode; } rsm_runtime_t;
rsm_status_t rsm_runtime_required_memory(const uint8_t *,size_t,size_t *);
rsm_status_t rsm_runtime_init(rsm_runtime_t *,void *,size_t,const rsm_hal_t *,void *);
void rsm_runtime_deinit(rsm_runtime_t *);
rsm_status_t rsm_runtime_load_image(rsm_runtime_t *,const uint8_t *,size_t);
rsm_status_t rsm_runtime_unload_program(rsm_runtime_t *);
rsm_status_t rsm_runtime_set_mode(rsm_runtime_t *,rsm_mode_t);
rsm_mode_t rsm_runtime_get_mode(const rsm_runtime_t *);
rsm_status_t rsm_runtime_scan(rsm_runtime_t *);
rsm_status_t rsm_runtime_read_tag(const rsm_runtime_t *,rsm_tag_id_t,rsm_value_t *);
rsm_status_t rsm_runtime_read_member(const rsm_runtime_t *,rsm_tag_id_t,rsm_member_id_t,rsm_value_t *);
rsm_status_t rsm_runtime_write_tag(rsm_runtime_t *,rsm_tag_id_t,const rsm_value_t *);
rsm_status_t rsm_runtime_force_tag(rsm_runtime_t *,rsm_tag_id_t,const rsm_value_t *);
rsm_status_t rsm_runtime_clear_force(rsm_runtime_t *,rsm_tag_id_t);
rsm_status_t rsm_runtime_clear_all_forces(rsm_runtime_t *);
rsm_status_t rsm_runtime_snapshot(const rsm_runtime_t *,rsm_snapshot_writer_t *);
rsm_status_t rsm_runtime_get_diagnostics(const rsm_runtime_t *,rsm_runtime_diagnostics_t *);
const rsm_fault_t *rsm_runtime_last_fault(const rsm_runtime_t *);
#endif
