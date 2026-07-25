#include "rsmicro/rsm_link.h"
#include <assert.h>
#include <string.h>
int main(void){uint8_t b[128],store[128];size_t n;const uint8_t p[]={1,2,3};rsm_link_frame_t in={1,0,42,7,0,p,3},out;rsm_link_stream_t s;assert(rsm_link_frame_encode(&in,b,sizeof b,&n)==RSM_LINK_OK);assert(n==31);assert(rsm_link_frame_decode(b,n,&out)==RSM_LINK_OK);assert(out.request_id==42&&out.payload_length==3&&!memcmp(out.payload,p,3));b[n-1]^=1;assert(rsm_link_frame_decode(b,n,&out)==RSM_LINK_BAD_CRC);b[n-1]^=1;rsm_link_stream_init(&s,store,sizeof store);assert(rsm_link_stream_feed(&s,b,1,&out)==RSM_LINK_INCOMPLETE);assert(rsm_link_stream_feed(&s,b+1,n-1,&out)==RSM_LINK_OK);return 0;}
