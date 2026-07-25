#include "rsmicro/rsm_node_queue.h"
#include <string.h>
void rsm_node_queue_init(rsm_node_queue_t*q){memset(q,0,sizeof *q);}
int rsm_node_queue_push(rsm_node_queue_t*q,const rsm_node_command_t*c){size_t tail;if(q->count==RSM_NODE_QUEUE_CAPACITY)return 0;tail=(q->head+q->count)%RSM_NODE_QUEUE_CAPACITY;q->items[tail]=*c;q->count++;if(q->count>q->high_water)q->high_water=q->count;return 1;}
int rsm_node_queue_pop(rsm_node_queue_t*q,rsm_node_command_t*c){if(!q->count)return 0;*c=q->items[q->head];q->head=(q->head+1)%RSM_NODE_QUEUE_CAPACITY;q->count--;return 1;}
