#include "rsmicro/rsm_image.h"
#include "rsmicro/rsm_runtime.h"
#include <stddef.h>
#include <stdio.h>
#include <string.h>

int main(void){rsm_runtime_t r;unsigned char arena[256];rsm_hal_t h;memset(&h,0,sizeof h);if(strcmp(rsm_status_name(RSM_STATUS_OK),"OK"))return 1;if(rsm_runtime_init(&r,arena,sizeof arena,&h,NULL)!=RSM_STATUS_INVALID_ARGUMENT)return 2;if(rsm_runtime_abi_major()!=1u||rsm_runtime_abi_minor()!=2u||rsm_instruction_abi()!=2u)return 3;if(rsm_runtime_object_size()!=sizeof(rsm_runtime_t)||strcmp(rsm_mode_name(RSM_MODE_RUN),"RUN"))return 4;if(sizeof(rsm_image_info_t)!=24u||offsetof(rsm_image_info_t,major)!=0u||offsetof(rsm_image_info_t,minor)!=1u||offsetof(rsm_image_info_t,profile_id)!=2u||offsetof(rsm_image_info_t,instruction_abi)!=4u||offsetof(rsm_image_info_t,section_count)!=6u||offsetof(rsm_image_info_t,image_size)!=8u||offsetof(rsm_image_info_t,tag_count)!=12u||offsetof(rsm_image_info_t,instruction_count)!=16u||offsetof(rsm_image_info_t,rung_count)!=20u)return 5;puts("runtime API and ImageInfo ABI tests: 5 passed");return 0;}
