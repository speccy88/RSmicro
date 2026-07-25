#ifndef RSM_IMAGE_H
#define RSM_IMAGE_H
#include <stddef.h>
#include <stdint.h>
#include "rsm_status.h"
typedef struct { uint8_t major,minor; uint16_t profile_id,instruction_abi,section_count; uint32_t image_size,tag_count,instruction_count,rung_count; } rsm_image_info_t;
rsm_status_t rsm_runtime_validate_image(const uint8_t *,size_t,rsm_image_info_t *);
#endif
