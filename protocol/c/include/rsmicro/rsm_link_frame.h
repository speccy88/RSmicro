#ifndef RSM_LINK_FRAME_H
#define RSM_LINK_FRAME_H
#include <stddef.h>
#include <stdint.h>
#define RSM_LINK_HEADER_SIZE 24u
#define RSM_LINK_MIN_FRAME_SIZE 28u
#define RSM_LINK_MAX_FRAME_SIZE 1048576u
#define RSM_LINK_MAX_PAYLOAD_SIZE (RSM_LINK_MAX_FRAME_SIZE-RSM_LINK_MIN_FRAME_SIZE)
typedef enum { RSM_LINK_OK=0,RSM_LINK_INCOMPLETE=1,RSM_LINK_BAD_FRAME=-1,RSM_LINK_BAD_CRC=-2,RSM_LINK_LIMIT=-3,RSM_LINK_VERSION=-4 } rsm_link_status_t;
typedef struct {uint16_t message_type,message_flags; uint32_t request_id,sequence; uint8_t header_flags; const uint8_t *payload; uint32_t payload_length;} rsm_link_frame_t;
uint32_t rsm_link_crc32c(const uint8_t *data,size_t length);
rsm_link_status_t rsm_link_frame_encode(const rsm_link_frame_t *,uint8_t *,size_t,size_t *);
rsm_link_status_t rsm_link_frame_decode(const uint8_t *,size_t,rsm_link_frame_t *);
#endif
