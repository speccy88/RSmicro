#ifndef RSM_NODE_QUEUE_H
#define RSM_NODE_QUEUE_H
#include <stddef.h>
#include <stdint.h>
#define RSM_NODE_QUEUE_CAPACITY 64u
typedef struct {uint16_t type;uint32_t request_id;uint32_t tag_id;int32_t value;} rsm_node_command_t;
typedef struct {rsm_node_command_t items[RSM_NODE_QUEUE_CAPACITY];size_t head,count,high_water;} rsm_node_queue_t;
void rsm_node_queue_init(rsm_node_queue_t *);
int rsm_node_queue_push(rsm_node_queue_t *,const rsm_node_command_t *);
int rsm_node_queue_pop(rsm_node_queue_t *,rsm_node_command_t *);
#endif
