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
uint32_t rsm_runtime_abi_major(void);
uint32_t rsm_runtime_abi_minor(void);
uint32_t rsm_instruction_abi(void);
uint32_t rsm_image_format_major(void);
uint32_t rsm_image_format_minor(void);
uint32_t rsm_profile_id(void);
size_t rsm_runtime_object_size(void);
const char *rsm_mode_name(rsm_mode_t mode);
const char *rsm_type_name(rsm_data_type_t type);
const char *rsm_fault_category_name(rsm_fault_category_t category);
rsm_status_t rsm_runtime_required_memory(const uint8_t *,size_t,size_t *);
rsm_status_t rsm_runtime_init(rsm_runtime_t *,void *,size_t,const rsm_hal_t *,void *);
void rsm_runtime_deinit(rsm_runtime_t *);
rsm_status_t rsm_runtime_load_image(rsm_runtime_t *,const uint8_t *,size_t);
rsm_status_t rsm_runtime_unload_program(rsm_runtime_t *);
rsm_status_t rsm_runtime_set_mode(rsm_runtime_t *,rsm_mode_t);
rsm_status_t rsm_runtime_prescan(rsm_runtime_t *);
rsm_status_t rsm_runtime_postscan(rsm_runtime_t *);
rsm_mode_t rsm_runtime_get_mode(const rsm_runtime_t *);
rsm_status_t rsm_runtime_scan(rsm_runtime_t *);
rsm_status_t rsm_runtime_read_tag(const rsm_runtime_t *,rsm_tag_id_t,rsm_value_t *);
rsm_status_t rsm_runtime_read_member(const rsm_runtime_t *,rsm_tag_id_t,rsm_member_id_t,rsm_value_t *);
rsm_status_t rsm_runtime_write_tag(rsm_runtime_t *,rsm_tag_id_t,const rsm_value_t *);
rsm_status_t rsm_runtime_force_tag(rsm_runtime_t *,rsm_tag_id_t,const rsm_value_t *);
rsm_status_t rsm_runtime_clear_force(rsm_runtime_t *,rsm_tag_id_t);
rsm_status_t rsm_runtime_clear_all_forces(rsm_runtime_t *);
/* Bounded, observational record of successful scalar backing writes.  Values
 * are logical backing values even when a force overlay is active. */
#define RSM_RUNTIME_WRITE_TRACE_CAPACITY 64u
typedef struct { rsm_tag_id_t tag; rsm_value_t value; } rsm_runtime_write_trace_entry_t;
rsm_status_t rsm_runtime_clear_write_trace(rsm_runtime_t *);
rsm_status_t rsm_runtime_get_write_trace(const rsm_runtime_t *,rsm_runtime_write_trace_entry_t *,size_t,size_t *);
rsm_status_t rsm_runtime_snapshot(const rsm_runtime_t *,rsm_snapshot_writer_t *);
rsm_status_t rsm_runtime_snapshot_members(const rsm_runtime_t *,rsm_snapshot_member_writer_t *);
rsm_status_t rsm_runtime_get_diagnostics(const rsm_runtime_t *,rsm_runtime_diagnostics_t *);
const rsm_fault_t *rsm_runtime_last_fault(const rsm_runtime_t *);
#endif
