#include "rsmicro/rsm_link.h"
#include <stdio.h>
#include <string.h>

#define CHECK(EXPR) do { \
    if (!(EXPR)) { \
        fprintf(stderr, "check failed at line %d: %s\n", __LINE__, #EXPR); \
        return 1; \
    } \
} while (0)

int main(void) {
    uint8_t buffer[128], storage[128];
    size_t encoded_size = 0;
    const uint8_t payload[] = {1, 2, 3};
    rsm_link_frame_t input = {1, 0, 42, 7, 0, payload, 3}, output;
    rsm_link_stream_t stream;

    CHECK(rsm_link_frame_encode(&input, buffer, sizeof buffer, &encoded_size) == RSM_LINK_OK);
    CHECK(encoded_size == 31);
    CHECK(rsm_link_frame_decode(buffer, encoded_size, &output) == RSM_LINK_OK);
    CHECK(output.request_id == 42 && output.payload_length == 3 &&
          memcmp(output.payload, payload, 3) == 0);
    buffer[encoded_size - 1] ^= 1;
    CHECK(rsm_link_frame_decode(buffer, encoded_size, &output) == RSM_LINK_BAD_CRC);
    buffer[encoded_size - 1] ^= 1;
    rsm_link_stream_init(&stream, storage, sizeof storage);
    CHECK(rsm_link_stream_feed(&stream, buffer, 1, &output) == RSM_LINK_INCOMPLETE);
    CHECK(rsm_link_stream_feed(&stream, buffer + 1, encoded_size - 1, &output) == RSM_LINK_OK);
    return 0;
}
