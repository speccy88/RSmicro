#ifndef RSM_LINK_STREAM_H
#define RSM_LINK_STREAM_H
#include "rsm_link_frame.h"
typedef struct {uint8_t *storage; size_t capacity,length; int failed;} rsm_link_stream_t;
void rsm_link_stream_init(rsm_link_stream_t *,uint8_t *,size_t);
void rsm_link_stream_reset(rsm_link_stream_t *);
rsm_link_status_t rsm_link_stream_feed(rsm_link_stream_t *,const uint8_t *,size_t,rsm_link_frame_t *);
void rsm_link_stream_consume(rsm_link_stream_t *,const rsm_link_frame_t *);
#endif
