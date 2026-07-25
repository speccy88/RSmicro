#include "rsmicro/rsm_node_queue.h"
#include <assert.h>
int main(void){rsm_node_queue_t q;rsm_node_command_t a={1,2,3,4},b;size_t i;rsm_node_queue_init(&q);assert(!rsm_node_queue_pop(&q,&b));assert(rsm_node_queue_push(&q,&a));assert(rsm_node_queue_pop(&q,&b)&&b.request_id==2);for(i=0;i<RSM_NODE_QUEUE_CAPACITY;i++)assert(rsm_node_queue_push(&q,&a));assert(!rsm_node_queue_push(&q,&a));return 0;}
