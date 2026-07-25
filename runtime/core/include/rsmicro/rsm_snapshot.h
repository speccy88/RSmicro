#ifndef RSM_SNAPSHOT_H
#define RSM_SNAPSHOT_H
#include "rsm_types.h"
#include "rsm_status.h"
typedef rsm_status_t (*rsm_snapshot_value_fn)(void *,rsm_tag_id_t,const rsm_value_t *,const rsm_value_t *,rsm_bool_t);
typedef struct { void *context; rsm_snapshot_value_fn value; } rsm_snapshot_writer_t;
#endif
