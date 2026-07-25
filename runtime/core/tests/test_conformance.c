#include "rsmicro/rsm_opcodes.h"
#include <stdio.h>
int main(void){unsigned ops[]={RSM_OP_XIC,RSM_OP_XIO,RSM_OP_OTE,RSM_OP_OTL,RSM_OP_OTU,RSM_OP_ONS,RSM_OP_TON,RSM_OP_CTU,RSM_OP_CTD,RSM_OP_RES,RSM_OP_EQ,RSM_OP_NE,RSM_OP_GT,RSM_OP_GE,RSM_OP_LT,RSM_OP_LE,RSM_OP_MOV,RSM_OP_CLR,RSM_OP_ADD,RSM_OP_SUB,RSM_OP_MUL,RSM_OP_DIV,RSM_OP_NEG,RSM_OP_ABS};unsigned i;for(i=1;i<24;i++)if(ops[i]==ops[i-1])return 1;puts("opcode conformance fixtures: 24 registered");return 0;}
