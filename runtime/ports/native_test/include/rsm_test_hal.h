#ifndef RSM_TEST_HAL_H
#define RSM_TEST_HAL_H
#include "rsmicro/rsm_hal.h"
#define RSM_TEST_ENDPOINTS 64
typedef struct {uint64_t time_us,reads,writes,kicks; rsm_value_t inputs[RSM_TEST_ENDPOINTS],outputs[RSM_TEST_ENDPOINTS]; rsm_bool_t input_valid[RSM_TEST_ENDPOINTS]; rsm_bool_t output_valid[RSM_TEST_ENDPOINTS]; rsm_bool_t fail_read,fail_write,fail_watchdog;} rsm_test_hal_t;
void rsm_test_hal_init(rsm_test_hal_t *,rsm_hal_t *); void rsm_test_hal_set_time_us(rsm_test_hal_t *,uint64_t); void rsm_test_hal_advance_time_us(rsm_test_hal_t *,uint64_t); rsm_status_t rsm_test_hal_set_input(rsm_test_hal_t *,uint32_t,const rsm_value_t *); rsm_status_t rsm_test_hal_get_output(const rsm_test_hal_t *,uint32_t,rsm_value_t *);
#endif
