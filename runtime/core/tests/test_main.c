#include "rsmicro/rsm_runtime.h"
#include <stdio.h>
#include <string.h>
int main(void){rsm_runtime_t r;unsigned char arena[256];rsm_hal_t h;memset(&h,0,sizeof h);if(strcmp(rsm_status_name(RSM_STATUS_OK),"OK"))return 1;if(rsm_runtime_init(&r,arena,sizeof arena,&h,NULL)!=RSM_STATUS_INVALID_ARGUMENT)return 2;if(rsm_runtime_abi_major()!=1u||rsm_runtime_abi_minor()!=1u||rsm_instruction_abi()!=1u)return 3;if(rsm_runtime_object_size()!=sizeof(rsm_runtime_t)||strcmp(rsm_mode_name(RSM_MODE_RUN),"RUN"))return 4;puts("runtime API tests: 4 passed");return 0;}
