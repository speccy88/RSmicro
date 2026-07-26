#include "rsmicro/rsm_node_queue.h"
#include <stdio.h>

#define CHECK(EXPR) do { \
    if (!(EXPR)) { \
        fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #EXPR); \
        return 1; \
    } \
} while (0)

int main(void) {
    rsm_node_queue_t queue;
    rsm_node_command_t input = {1, 2, 3, 4}, output;
    size_t index;

    rsm_node_queue_init(&queue);
    CHECK(!rsm_node_queue_pop(&queue, &output));
    CHECK(rsm_node_queue_push(&queue, &input));
    CHECK(rsm_node_queue_pop(&queue, &output) && output.request_id == 2);
    for (index = 0; index < RSM_NODE_QUEUE_CAPACITY; index++)
        CHECK(rsm_node_queue_push(&queue, &input));
    CHECK(!rsm_node_queue_push(&queue, &input));
    return 0;
}
