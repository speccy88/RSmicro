#ifndef RSM_TYPES_H
#define RSM_TYPES_H
#include <stdint.h>
#include <stdbool.h>
typedef uint8_t rsm_bool_t; typedef int32_t rsm_dint_t; typedef float rsm_real_t;
#define RSM_FALSE ((rsm_bool_t)0u)
#define RSM_TRUE ((rsm_bool_t)1u)
typedef uint32_t rsm_tag_id_t; typedef uint8_t rsm_member_id_t;
typedef enum { RSM_TYPE_BOOL=1,RSM_TYPE_DINT=2,RSM_TYPE_REAL=3,RSM_TYPE_TIMER=4,RSM_TYPE_COUNTER=5 } rsm_data_type_t;
typedef struct { rsm_dint_t pre,acc; rsm_bool_t en,tt,dn; } rsm_timer_t;
typedef struct { rsm_dint_t pre,acc; rsm_bool_t cu,cd,dn,ov,un; } rsm_counter_t;
typedef struct { rsm_data_type_t type; union { rsm_bool_t boolean; rsm_dint_t dint; rsm_real_t real; } value; } rsm_value_t;
#endif
