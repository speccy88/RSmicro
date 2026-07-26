#include "rsmicro/rsm_image.h"
#include "rsmicro/rsm_runtime.h"
#include <stddef.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    rsm_runtime_t runtime;
    unsigned char arena[256];
    rsm_hal_t hal;
    const size_t actual_layout[]={
        sizeof(rsm_image_info_t),
        offsetof(rsm_image_info_t,major),
        offsetof(rsm_image_info_t,minor),
        offsetof(rsm_image_info_t,profile_id),
        offsetof(rsm_image_info_t,instruction_abi),
        offsetof(rsm_image_info_t,section_count),
        offsetof(rsm_image_info_t,image_size),
        offsetof(rsm_image_info_t,tag_count),
        offsetof(rsm_image_info_t,instruction_count),
        offsetof(rsm_image_info_t,rung_count)
    };
    const size_t expected_layout[]={24u,0u,1u,2u,4u,6u,8u,12u,16u,20u};
    size_t index;

    memset(&hal,0,sizeof hal);
    if(strcmp(rsm_status_name(RSM_STATUS_OK),"OK"))return 1;
    if(rsm_runtime_init(&runtime,arena,sizeof arena,&hal,NULL)!=RSM_STATUS_INVALID_ARGUMENT)return 2;
    if(rsm_runtime_abi_major()!=1u||rsm_runtime_abi_minor()!=2u||rsm_instruction_abi()!=2u)return 3;
    if(rsm_runtime_object_size()!=sizeof(rsm_runtime_t)||strcmp(rsm_mode_name(RSM_MODE_RUN),"RUN"))return 4;
    for(index=0u;index<sizeof actual_layout/sizeof actual_layout[0];index++){
        if(actual_layout[index]!=expected_layout[index])return 5;
    }
    puts("runtime API and ImageInfo ABI tests: 5 passed");
    return 0;
}
