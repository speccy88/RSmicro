#include "rsmicro/rsm_link_stream.h"
#include <string.h>
static uint32_t u32(const uint8_t*p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
void rsm_link_stream_init(rsm_link_stream_t*s,uint8_t*b,size_t n){s->storage=b;s->capacity=n;s->length=0;s->failed=0;}
void rsm_link_stream_reset(rsm_link_stream_t*s){s->length=0;s->failed=0;}
rsm_link_status_t rsm_link_stream_feed(rsm_link_stream_t*s,const uint8_t*d,size_t n,rsm_link_frame_t*f){size_t total;rsm_link_status_t status;if(s->failed)return RSM_LINK_BAD_FRAME;if(n>s->capacity-s->length){s->failed=1;return RSM_LINK_LIMIT;}memcpy(s->storage+s->length,d,n);s->length+=n;if(s->length<24)return RSM_LINK_INCOMPLETE;total=RSM_LINK_MIN_FRAME_SIZE+u32(s->storage+20);if(total>s->capacity||total>RSM_LINK_MAX_FRAME_SIZE){s->failed=1;return RSM_LINK_LIMIT;}if(s->length<total)return RSM_LINK_INCOMPLETE;status=rsm_link_frame_decode(s->storage,total,f);if(status!=RSM_LINK_OK)s->failed=1;return status;}
void rsm_link_stream_consume(rsm_link_stream_t*s,const rsm_link_frame_t*f){size_t n=RSM_LINK_MIN_FRAME_SIZE+f->payload_length;if(n<=s->length){memmove(s->storage,s->storage+n,s->length-n);s->length-=n;}}
