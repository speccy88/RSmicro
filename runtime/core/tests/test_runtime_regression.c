#include "rsmicro/rsm_runtime.h"
#include "rsmicro/rsm_opcodes.h"
#include "rsm_conformance_fixtures.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define HEADER 72u
#define DESC 20u
#define NONE UINT32_MAX

typedef struct { uint64_t now, reads, writes, watchdogs; } hal_counts_t;
typedef struct { unsigned values, members, states, rungs; uint32_t last_slot; rsm_runtime_diagnostics_t diag; rsm_fault_t fault; } snapshot_t;

static uint16_t get16(const uint8_t *p) { return (uint16_t)(p[0] | ((uint16_t)p[1] << 8)); }
static uint32_t get32(const uint8_t *p) { return (uint32_t)p[0] | ((uint32_t)p[1] << 8) | ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24); }
static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); }
static void put32(uint8_t *p, uint32_t v) { p[0]=(uint8_t)v; p[1]=(uint8_t)(v>>8); p[2]=(uint8_t)(v>>16); p[3]=(uint8_t)(v>>24); }
static uint32_t crc(const uint8_t *p, size_t n) { uint32_t c=UINT32_MAX; size_t i; unsigned b; for(i=0;i<n;i++){c^=(i>=68u&&i<72u)?0u:p[i];for(b=0;b<8u;b++)c=(c>>1)^((0u-(c&1u))&0xedb88320u);} return ~c; }
static void seal(uint8_t *p,size_t n) { put32(p+68u,crc(p,n)); }
static uint8_t *desc(uint8_t *p,unsigned i) { return p+HEADER+(size_t)i*DESC; }
static uint8_t *section(uint8_t *p,uint16_t kind) { unsigned i; for(i=0;i<get16(p+18u);i++)if(get16(desc(p,i))==kind)return p+get32(desc(p,i)+4u); return NULL; }
static const rsm_conformance_fixture_t *fixture(const char *id) { size_t i; for(i=0;i<rsm_conformance_fixture_count;i++)if(strcmp(rsm_conformance_fixtures[i].id,id)==0)return &rsm_conformance_fixtures[i]; return NULL; }
static int check(rsm_status_t got,rsm_status_t want,const char *what) { if(got!=want){fprintf(stderr,"%s: got %s expected %s\n",what,rsm_status_name(got),rsm_status_name(want));return 1;}return 0; }
static uint64_t tick(void *p) { return ((hal_counts_t *)p)->now; }
static rsm_status_t read_input(void *p,uint32_t id,rsm_value_t *v) { (void)id;(void)v;((hal_counts_t *)p)->reads++;return RSM_STATUS_OK; }
static rsm_status_t write_output(void *p,uint32_t id,const rsm_value_t *v) { (void)id;(void)v;((hal_counts_t *)p)->writes++;return RSM_STATUS_OK; }
static rsm_status_t watchdog(void *p) { ((hal_counts_t *)p)->watchdogs++;return RSM_STATUS_OK; }
static rsm_hal_t counted_hal(void) { rsm_hal_t h; memset(&h,0,sizeof h);h.monotonic_time_us=tick;h.read_input=read_input;h.write_output=write_output;h.kick_watchdog=watchdog;return h; }

/* Every malformed candidate is CRC-resealed when its original byte length is
 * retained.  The attempted load must leave a fully live program (mode, forced
 * effective value and diagnostics) untouched. */
static int reject_atomic(const char *name,const rsm_conformance_fixture_t *good,const uint8_t *bad,size_t bad_n) {
    rsm_runtime_t r; rsm_hal_t h=counted_hal(); hal_counts_t hc={0}; uint8_t arena[65536];
    rsm_value_t before,after,force; rsm_runtime_diagnostics_t d0,d1; rsm_image_info_t info; int fail=0;
    if(check(rsm_runtime_init(&r,arena,sizeof arena,&h,&hc),RSM_STATUS_OK,"atomic init") ||
       check(rsm_runtime_load_image(&r,good->image,good->image_size),RSM_STATUS_OK,"atomic good load") ||
       check(rsm_runtime_read_tag(&r,0u,&force),RSM_STATUS_OK,"atomic force source")) return 1;
    if(force.type==RSM_TYPE_BOOL) force.value.boolean=!force.value.boolean;
    else if(force.type==RSM_TYPE_DINT) force.value.dint+=1;
    else force.value.real+=1.0f;
    if(check(rsm_runtime_force_tag(&r,0u,&force),RSM_STATUS_OK,"atomic force") ||
       check(rsm_runtime_read_tag(&r,0u,&before),RSM_STATUS_OK,"atomic before") ||
       check(rsm_runtime_get_diagnostics(&r,&d0),RSM_STATUS_OK,"atomic diag before")) return 1;
    if(rsm_runtime_validate_image(bad,bad_n,&info)==RSM_STATUS_OK){fprintf(stderr,"%s passed standalone validator\n",name);fail=1;}
    if(rsm_runtime_load_image(&r,bad,bad_n)==RSM_STATUS_OK){fprintf(stderr,"%s accepted\n",name);fail=1;}
    if(check(rsm_runtime_read_tag(&r,0u,&after),RSM_STATUS_OK,"atomic after") ||
       check(rsm_runtime_get_diagnostics(&r,&d1),RSM_STATUS_OK,"atomic diag after")) fail=1;
    if(rsm_runtime_get_mode(&r)!=RSM_MODE_PROGRAM || before.type!=after.type || memcmp(&before.value,&after.value,sizeof before.value)!=0 ||
       memcmp(&d0,&d1,sizeof d0)!=0){fprintf(stderr,"%s changed active program\n",name);fail=1;}
    rsm_runtime_deinit(&r); return fail;
}
static uint8_t *instruction(uint8_t *code,unsigned wanted) { unsigned n=0; size_t off=0; while(n<wanted){off+=12u+(size_t)code[off+1u]*8u;n++;} return code+off; }

/* Constructs binary-only images; the validator must not need JSON metadata. */
static size_t make_image(uint8_t *image, unsigned instructions, unsigned rungs, int branches) {
    const size_t data=HEADER+16u*DESC, code_size=(size_t)instructions*12u+(branches?0u:(size_t)instructions*8u);
    const size_t tag_size=branches?4u:24u, rung_size=4u+(size_t)rungs*12u, total=data+code_size+tag_size+rung_size;
    uint8_t *code,*tags,*rg; unsigned i;
    memset(image,0,total); memcpy(image,"RSM1",4); image[4]=2u; put16(image+6u,HEADER); put32(image+8u,(uint32_t)total); put32(image+12u,1u); put16(image+16u,2u); put16(image+18u,16u);
    for(i=0;i<16u;i++){ uint8_t *d=desc(image,i); put16(d,(uint16_t)(i+1u)); put32(d+4u,(uint32_t)data); }
    code=image+data; tags=code+code_size; rg=tags+tag_size;
    put32(desc(image,7u)+4u,(uint32_t)(code-image)); put32(desc(image,7u)+8u,(uint32_t)code_size);
    put32(desc(image,14u)+4u,(uint32_t)(tags-image)); put32(desc(image,14u)+8u,(uint32_t)tag_size);
    put32(desc(image,15u)+4u,(uint32_t)(rg-image)); put32(desc(image,15u)+8u,(uint32_t)rung_size);
    if(branches) for(i=0;i<instructions;i++){ code[i*12u]=RSM_OP_BRANCH_BEGIN; put32(code+i*12u+8u,NONE); }
    else { put32(tags,1u); tags[4u]=RSM_TYPE_BOOL; for(i=0;i<instructions;i++){ uint8_t *q=code+i*20u; q[0]=RSM_OP_XIC; q[1]=1u; put32(q+8u,NONE); q[12u]=1u; q[13u]=RSM_TYPE_BOOL; } }
    put32(rg,rungs); for(i=0;i<rungs;i++){ uint8_t *q=rg+4u+(size_t)i*12u; put32(q,(i==rungs-1u)?1u:0u); put32(q+4u,i); put32(q+8u,1u); }
    seal(image,total); return total;
}

static size_t make_scale_image(uint8_t *image,uint32_t count,int tag_heavy) {
    size_t data=HEADER+16u*DESC,code_size=tag_heavy?20u:(size_t)count*20u,tag_size=tag_heavy?4u+(size_t)count*20u:24u,rung_size=4u+(size_t)(tag_heavy?1u:count)*12u,total=data+code_size+tag_size+rung_size;
    uint8_t *code=image+data,*tags=code+code_size,*rungs=tags+tag_size; uint32_t i;
    memset(image,0,total);memcpy(image,"RSM1",4);image[4]=2u;put16(image+6u,HEADER);put32(image+8u,(uint32_t)total);put32(image+12u,1u);put16(image+16u,2u);put16(image+18u,16u);
    for(i=0;i<16u;i++){uint8_t*d=desc(image,i);put16(d,(uint16_t)(i+1u));put32(d+4u,(uint32_t)data);}
    put32(desc(image,7u)+4u,(uint32_t)(code-image));put32(desc(image,7u)+8u,(uint32_t)code_size);put32(desc(image,14u)+4u,(uint32_t)(tags-image));put32(desc(image,14u)+8u,(uint32_t)tag_size);put32(desc(image,15u)+4u,(uint32_t)(rungs-image));put32(desc(image,15u)+8u,(uint32_t)rung_size);
    put32(tags,tag_heavy?count:1u);for(i=0;i<(tag_heavy?count:1u);i++)tags[4u+(size_t)i*20u]=RSM_TYPE_BOOL;
    for(i=0;i<(tag_heavy?1u:count);i++){uint8_t*q=code+(size_t)i*20u;q[0]=RSM_OP_XIC;q[1]=1u;put32(q+8u,NONE);q[12u]=1u;q[13u]=RSM_TYPE_BOOL;}
    put32(rungs,tag_heavy?1u:count);for(i=0;i<(tag_heavy?1u:count);i++){uint8_t*q=rungs+4u+(size_t)i*12u;put32(q,0u);put32(q+4u,i);put32(q+8u,1u);}seal(image,total);return total;
}
static int hostile_scale_contract(void) {
    const uint32_t counts[]={65535u,65536u,65537u};
    unsigned kind,index;
    int failures=0;
    for(kind=0u;kind<2u;kind++){
        for(index=0u;index<sizeof counts/sizeof counts[0];index++){
            size_t capacity=(size_t)HEADER+16u*DESC+(size_t)counts[index]*32u+64u,n,need;
            uint8_t *image=malloc(capacity);
            rsm_image_info_t info;
            if(!image)return 1;
            n=make_scale_image(image,counts[index],kind==0u);
            if(check(rsm_runtime_validate_image(image,n,&info),RSM_STATUS_OK,"scale validate")||check(rsm_runtime_required_memory(image,n,&need),RSM_STATUS_OK,"scale required memory")||need==0u||info.tag_count!=(kind==0u?counts[index]:1u)||info.rung_count!=(kind==0u?1u:counts[index]))failures++;
            if(rsm_runtime_validate_image(image,n-1u,&info)==RSM_STATUS_OK){fputs("scale truncation accepted\n",stderr);failures++;}
            free(image);
        }
    }
    puts("hostile tag/rung boundaries: 65535/65536/65537 passed");
    return failures;
}

static size_t make_state_scale_image(uint8_t *image,uint32_t count,int many_rungs) {
    size_t data=HEADER+16u*DESC,code_size=(size_t)count*20u,tag_size=24u,rung_size=4u+(size_t)(many_rungs?count:1u)*12u,total=data+code_size+tag_size+rung_size;
    uint8_t *code=image+data,*tags=code+code_size,*rungs=tags+tag_size;uint32_t i;
    memset(image,0,total);memcpy(image,"RSM1",4);image[4]=2u;put16(image+6u,HEADER);put32(image+8u,(uint32_t)total);put32(image+12u,1u);put16(image+16u,2u);put16(image+18u,16u);
    for(i=0;i<16u;i++){uint8_t*d=desc(image,i);put16(d,(uint16_t)(i+1u));put32(d+4u,(uint32_t)data);}
    put32(desc(image,7u)+4u,(uint32_t)(code-image));put32(desc(image,7u)+8u,(uint32_t)code_size);
    put32(desc(image,14u)+4u,(uint32_t)(tags-image));put32(desc(image,14u)+8u,(uint32_t)tag_size);
    put32(desc(image,15u)+4u,(uint32_t)(rungs-image));put32(desc(image,15u)+8u,(uint32_t)rung_size);
    put32(tags,1u);tags[4u]=RSM_TYPE_TIMER;
    for(i=0;i<count;i++){uint8_t*q=code+(size_t)i*20u;q[0]=RSM_OP_TON;q[1]=1u;put32(q+8u,i*2u);q[12u]=1u;q[13u]=RSM_TYPE_TIMER;}
    put32(rungs,many_rungs?count:1u);
    if(many_rungs)for(i=0;i<count;i++){uint8_t*q=rungs+4u+(size_t)i*12u;put32(q,0u);put32(q+4u,i);put32(q+8u,1u);}
    else {put32(rungs+4u,0u);put32(rungs+8u,0u);put32(rungs+12u,count);}
    seal(image,total);return total;
}

static int hostile_state_scale_contract(void) {
    const uint32_t counts[]={65535u,65536u,65537u};unsigned index;int failures=0;clock_t started=clock();
    for(index=0u;index<sizeof counts/sizeof counts[0];index++){
        int many_rungs=index+1u==sizeof counts/sizeof counts[0];
        size_t capacity=HEADER+16u*DESC+(size_t)counts[index]*32u+64u,n,need=0u;uint8_t *image=malloc(capacity);rsm_image_info_t info={0};
        if(!image)return 1;
        n=make_state_scale_image(image,counts[index],many_rungs);
        if(check(rsm_runtime_validate_image(image,n,&info),RSM_STATUS_OK,"state scale validate")||
           check(rsm_runtime_required_memory(image,n,&need),RSM_STATUS_OK,"state scale required")||
           info.instruction_count!=counts[index]||info.rung_count!=(many_rungs?counts[index]:1u))failures++;
        if(many_rungs){
            uint8_t *arena=malloc(need);rsm_runtime_t runtime;rsm_hal_t hal=counted_hal();hal_counts_t counts_hal={0};
            if(!arena){free(image);return 1;}
            if(check(rsm_runtime_init(&runtime,arena,need,&hal,&counts_hal),RSM_STATUS_OK,"state scale init")||
               check(rsm_runtime_load_image(&runtime,image,n),RSM_STATUS_OK,"state scale load")||
               check(rsm_runtime_set_mode(&runtime,RSM_MODE_RUN),RSM_STATUS_OK,"state scale mode")||
               check(rsm_runtime_scan(&runtime),RSM_STATUS_OK,"state scale scan"))failures++;
            rsm_runtime_deinit(&runtime);free(arena);
        }
        free(image);
    }
    {
        uint8_t image[512],arena[1024],*code;size_t n,need=0u;rsm_image_info_t info;rsm_runtime_t runtime;rsm_hal_t hal=counted_hal();hal_counts_t counts_hal={0};
        n=make_state_scale_image(image,2u,0);code=section(image,8u);put32(code+8u,2u);put32(code+28u,1u);seal(image,n);
        if(check(rsm_runtime_validate_image(image,n,&info),RSM_STATUS_BAD_IMAGE,"descending state slots validate")||
           check(rsm_runtime_required_memory(image,n,&need),RSM_STATUS_BAD_IMAGE,"descending state slots size")||
           check(rsm_runtime_init(&runtime,arena,sizeof arena,&hal,&counts_hal),RSM_STATUS_OK,"descending state slots init")||
           check(rsm_runtime_load_image(&runtime,image,n),RSM_STATUS_BAD_IMAGE,"descending state slots load"))failures++;
        rsm_runtime_deinit(&runtime);
    }
    if((double)(clock()-started)/(double)CLOCKS_PER_SEC>10.0){fputs("state scale validation/scan exceeded 10 seconds\n",stderr);failures++;}
    puts("hostile stateful boundaries: 65535/65536/65537 validate and 65537-state/65537-rung scan passed");return failures;
}

static size_t make_nested_branch_image(uint8_t *image) {
    uint8_t *code,*rg; unsigned i,record=0u; size_t n=make_image(image,128u,128u,1);
    rg=section(image,16u); put32(rg,1u); put32(rg+4u,0u); put32(rg+8u,0u); put32(rg+12u,128u); put32(desc(image,15u)+8u,16u);
    code=section(image,8u);
    for(i=0;i<32u;i++){ code[record++*12u]=RSM_OP_BRANCH_BEGIN; code[record++*12u]=RSM_OP_BRANCH_LANE_BEGIN; }
    for(i=0;i<32u;i++){ code[record++*12u]=RSM_OP_BRANCH_LANE_END; code[record++*12u]=RSM_OP_BRANCH_END; }
    seal(image,n); return n;
}

static int malformed_matrix(void) {
    const rsm_conformance_fixture_t *base=fixture("abs-core-001"),*ton=fixture("ton-core-001"),*branch=fixture("branch-nested-core-001");
    uint8_t image[65536]; uint8_t *tags,*code,*rungs,*d; size_t n; unsigned i,passed=0; int failures=0;
    if(!base||!ton||!branch)return 1;
#define BAD(NAME, ...) do { memcpy(image,base->image,base->image_size); n=base->image_size; __VA_ARGS__; seal(image,n); failures+=reject_atomic(NAME,base,image,n); passed++; } while(0)
    BAD("header profile",put32(image+12u,99u));
    BAD("header ABI",image[16u]=99u);
    BAD("header size",put32(image+8u,(uint32_t)n-1u));
    /* all required sections: duplicate, missing, overlap, and out-of-bounds */
    for(i=0;i<16u;i++){ BAD("section duplicate",put32(desc(image,i),get16(desc(image,(i+1u)%16u)))); BAD("section missing",put32(desc(image,i),17u)); BAD("section overlap",put32(desc(image,i)+4u,get32(desc(image,(i+1u)%16u)+4u))); BAD("section bounds",put32(desc(image,i)+4u,(uint32_t)n)); }
    /* Every truncation boundary is independently passed to the validator/load. */
    for(i=0;i<16u;i++){ memcpy(image,base->image,base->image_size); n=base->image_size-(i+1u); failures+=reject_atomic("truncated image",base,image,n); passed++; }
    BAD("tag type range",tags=section(image,15u),tags[4u]=6u);
    BAD("tag storage range",tags=section(image,15u),tags[5u]=3u);
    BAD("tag reserved",tags=section(image,15u),tags[7u]=1u);
    BAD("operand opcode",code=section(image,8u),code[0]=99u);
    BAD("operand arity",code=section(image,8u),code[1]=3u);
    BAD("operand kind",code=section(image,8u),code[12u]=3u);
    BAD("operand type",code=section(image,8u),code[13u]=RSM_TYPE_BOOL);
    BAD("operand member range",code=section(image,8u),code[14u]=99u);
    BAD("operand tag range",code=section(image,8u),put32(code+16u,UINT32_MAX));
    BAD("operand writable",tags=section(image,15u),tags[4u+20u+1u]=1u);
    BAD("rung start",rungs=section(image,16u),put32(rungs+8u,1u));
    BAD("rung count",rungs=section(image,16u),put32(rungs+12u,UINT32_MAX));
    BAD("stream record truncation",d=desc(image,7u),put32(d+8u,get32(d+8u)-1u));
#undef BAD
    /* Stateful records are mutated on a canonical TON image. */
    memcpy(image,ton->image,ton->image_size); n=ton->image_size; code=section(image,8u); instruction(code,1u)[8u]=0xfeu;instruction(code,1u)[9u]=0xffu;instruction(code,1u)[10u]=0xffu;instruction(code,1u)[11u]=0xffu;seal(image,n);failures+=reject_atomic("negative state slot",ton,image,n);passed++;
    memcpy(image,ton->image,ton->image_size); n=ton->image_size; code=section(image,8u); instruction(code,1u)[12u]=2u;seal(image,n);failures+=reject_atomic("state operand kind",ton,image,n);passed++;
    memcpy(image,fixture("ctu-core-001")->image,fixture("ctu-core-001")->image_size); n=fixture("ctu-core-001")->image_size; code=section(image,8u); instruction(code,0u)[0u]=RSM_OP_CTU;instruction(code,0u)[8u]=0u;instruction(code,0u)[9u]=0u;instruction(code,0u)[10u]=0u;instruction(code,0u)[11u]=0u;instruction(code,0u)[13u]=RSM_TYPE_COUNTER;put32(instruction(code,0u)+16u,1u);seal(image,n);failures+=reject_atomic("state slot duplicate",fixture("ctu-core-001"),image,n);passed++;
    /* Branch structural, escape and depth cases; each mutation remains CRC valid. */
    memcpy(image,branch->image,branch->image_size);n=branch->image_size;code=section(image,8u);code[0]=RSM_OP_BRANCH_END;seal(image,n);failures+=reject_atomic("branch unmatched end",branch,image,n);passed++;
    memcpy(image,branch->image,branch->image_size);n=branch->image_size;code=section(image,8u);code[0]=RSM_OP_BRANCH_LANE_END;seal(image,n);failures+=reject_atomic("branch escaped lane",branch,image,n);passed++;
    memcpy(image,branch->image,branch->image_size);n=branch->image_size;code=section(image,8u);code[1]=1u;seal(image,n);failures+=reject_atomic("branch arity",branch,image,n);passed++;
    /* Independently constructed binary metadata proves routine IDs and rung bounds
     * are admitted without consulting JSON.  Each candidate is CRC-resealed. */
    n=make_image(image,3u,3u,0); if(rsm_runtime_validate_image(image,n,&(rsm_image_info_t){0})!=RSM_STATUS_OK){fputs("constructed routine image invalid\n",stderr);failures++;}
    rungs=section(image,16u); put32(rungs+4u,UINT32_MAX); seal(image,n); failures+=reject_atomic("routine id UINT32_MAX",base,image,n); passed++;
    n=make_image(image,3u,3u,0); rungs=section(image,16u); put32(rungs+4u,1u); seal(image,n); failures+=reject_atomic("routine id must begin zero",base,image,n); passed++;
    n=make_image(image,3u,3u,0); rungs=section(image,16u); put32(rungs+16u,2u); seal(image,n); failures+=reject_atomic("routine id gap",base,image,n); passed++;
    n=make_image(image,3u,3u,0); rungs=section(image,16u); put32(rungs+16u,1u); put32(rungs+28u,0u); seal(image,n); failures+=reject_atomic("routine id backtrack",base,image,n); passed++;
    n=make_image(image,3u,3u,0); rungs=section(image,16u); put32(rungs+20u,2u); seal(image,n); failures+=reject_atomic("routine rung boundary",base,image,n); passed++;
    n=make_image(image,3u,3u,0); rungs=section(image,16u); put32(rungs+12u,2u); seal(image,n); failures+=reject_atomic("routine rung overlap",base,image,n); passed++;
    /* Start from an independently constructed, valid depth-32 binary image,
     * mutate its deepest lane delimiter into a 33rd BRANCH_BEGIN, then reseal. */
    n=make_nested_branch_image(image); if(rsm_runtime_validate_image(image,n,&(rsm_image_info_t){0})!=RSM_STATUS_OK){fputs("constructed depth-32 image invalid\n",stderr);failures++;}
    code=section(image,8u); code[63u*12u]=RSM_OP_BRANCH_BEGIN; seal(image,n); failures+=reject_atomic("branch nesting over 32",base,image,n); passed++;
    printf("malformed CRC-resealed categories: %u attempted\n",passed);
    return failures;
}

static rsm_status_t snap_value(void *p,rsm_tag_id_t id,const rsm_value_t *logical,const rsm_value_t *effective,rsm_bool_t forced) { snapshot_t *s=p;(void)id;(void)logical;(void)effective;(void)forced;s->values++;return RSM_STATUS_OK; }
static rsm_status_t snap_member(void *p,rsm_tag_id_t id,rsm_member_id_t m,const rsm_value_t *v) { snapshot_t *s=p;(void)id;(void)m;(void)v;s->members++;return RSM_STATUS_OK; }
static rsm_status_t snap_state(void *p,uint8_t mode,const rsm_runtime_diagnostics_t *d,const rsm_fault_t *f,uint32_t slot,uint8_t edge,uint8_t valid,uint64_t time) { snapshot_t*s=p;(void)mode;(void)edge;(void)valid;(void)time;s->states++;s->last_slot=slot;s->diag=*d;s->fault=*f;return RSM_STATUS_OK; }
static rsm_status_t snap_rung(void *p,uint32_t rung,rsm_bool_t power) { snapshot_t*s=p;(void)rung;(void)power;s->rungs++;return RSM_STATUS_OK; }
static int snapshots_are_immutable(void) {
    const rsm_conformance_fixture_t *f=fixture("ton-core-001"),*fault=fixture("div-fault-core-001"); rsm_runtime_t a,b; uint8_t aa[65536],bb[65536]; hal_counts_t ha={0},hb={0}; rsm_hal_t h=counted_hal(); rsm_snapshot_writer_t w; snapshot_t s; rsm_runtime_diagnostics_t before,after; int failures=0; unsigned mode; uint64_t reads,writes,watchdogs;
    if(!f||!fault)return 1;
    memset(&w,0,sizeof w);w.value=snap_value;w.member=snap_member;w.state=snap_state;w.rung_power=snap_rung;
    if(check(rsm_runtime_init(&a,aa,sizeof aa,&h,&ha),RSM_STATUS_OK,"snapshot init a")||check(rsm_runtime_init(&b,bb,sizeof bb,&h,&hb),RSM_STATUS_OK,"snapshot init b")||check(rsm_runtime_load_image(&a,f->image,f->image_size),RSM_STATUS_OK,"snapshot load a")||check(rsm_runtime_load_image(&b,f->image,f->image_size),RSM_STATUS_OK,"snapshot load b"))return 1;
    for(mode=0;mode<3u;mode++){if(mode==1u)check(rsm_runtime_set_mode(&a,RSM_MODE_RUN),RSM_STATUS_OK,"snapshot RUN");if(mode==2u){check(rsm_runtime_set_mode(&a,RSM_MODE_PROGRAM),RSM_STATUS_OK,"snapshot PROGRAM");check(rsm_runtime_set_mode(&a,RSM_MODE_TEST),RSM_STATUS_OK,"snapshot TEST");}if(mode)check(rsm_runtime_scan(&a),RSM_STATUS_OK,"snapshot scan");if(check(rsm_runtime_get_diagnostics(&a,&before),RSM_STATUS_OK,"snapshot diagnostics"))return 1;reads=ha.reads;writes=ha.writes;watchdogs=ha.watchdogs;memset(&s,0,sizeof s);w.context=&s;if(check(rsm_runtime_snapshot(&a,&w),RSM_STATUS_OK,"snapshot full")||check(rsm_runtime_snapshot(&a,&w),RSM_STATUS_OK,"snapshot repeat")||check(rsm_runtime_get_diagnostics(&a,&after),RSM_STATUS_OK,"snapshot after"))return 1;if(memcmp(&before,&after,sizeof before)||!s.values||!s.members||!s.states||!s.rungs||reads!=ha.reads||writes!=ha.writes||watchdogs!=ha.watchdogs){fprintf(stderr,"snapshot did not preserve or expose complete state in mode %u\n",mode);failures++;}}
    /* A faulted runtime still offers an observational snapshot and cannot affect peer B. */
    rsm_runtime_deinit(&a);check(rsm_runtime_init(&a,aa,sizeof aa,&h,&ha),RSM_STATUS_OK,"fault init");check(rsm_runtime_load_image(&a,fault->image,fault->image_size),RSM_STATUS_OK,"fault load");check(rsm_runtime_set_mode(&a,RSM_MODE_RUN),RSM_STATUS_OK,"fault run");check(rsm_runtime_scan(&a),RSM_STATUS_FAULTED,"fault scan");memset(&s,0,sizeof s);w.context=&s;if(check(rsm_runtime_snapshot(&a,&w),RSM_STATUS_OK,"fault snapshot")||rsm_runtime_get_mode(&a)!=RSM_MODE_FAULTED||s.states!=1u||s.last_slot!=UINT32_MAX||s.fault.category!=RSM_FAULT_NUMERIC||s.fault.code!=2u){fputs("fault snapshot envelope missing or malformed\n",stderr);failures++;}
    rsm_runtime_deinit(&a);rsm_runtime_deinit(&b);printf("snapshot immutability: PROGRAM/RUN/TEST/FAULT × two instances passed\n");return failures;
}

static int lifecycle_matrix(void) {
    const char *ids[]={"ote-core-001","ton-core-001","ctu-core-001","ctd-core-001","ons-core-001"}; unsigned i; int failures=0;
    for(i=0;i<sizeof ids/sizeof ids[0];i++){const rsm_conformance_fixture_t*f=fixture(ids[i]);rsm_runtime_t r;uint8_t arena[65536];hal_counts_t hc={0};rsm_hal_t h=counted_hal();rsm_runtime_diagnostics_t d;uint64_t writes; if(!f)return 1;if(check(rsm_runtime_init(&r,arena,sizeof arena,&h,&hc),RSM_STATUS_OK,"lifecycle init")||check(rsm_runtime_load_image(&r,f->image,f->image_size),RSM_STATUS_OK,"lifecycle load")||check(rsm_runtime_get_diagnostics(&r,&d),RSM_STATUS_OK,"lifecycle d0"))return 1;if(d.scan_count){fputs("load scanned\n",stderr);failures++;}check(rsm_runtime_set_mode(&r,RSM_MODE_RUN),RSM_STATUS_OK,"PROGRAM RUN");check(rsm_runtime_get_diagnostics(&r,&d),RSM_STATUS_OK,"run transition");if(d.scan_count){fputs("RUN transition scanned\n",stderr);failures++;}check(rsm_runtime_scan(&r),RSM_STATUS_OK,"RUN scan");check(rsm_runtime_set_mode(&r,RSM_MODE_PROGRAM),RSM_STATUS_OK,"RUN PROGRAM");check(rsm_runtime_get_diagnostics(&r,&d),RSM_STATUS_OK,"program transition");if(d.scan_count!=1u){fputs("PROGRAM transition effect count wrong\n",stderr);failures++;}check(rsm_runtime_set_mode(&r,RSM_MODE_TEST),RSM_STATUS_OK,"PROGRAM TEST");writes=hc.writes;check(rsm_runtime_scan(&r),RSM_STATUS_OK,"TEST scan");if(hc.writes!=writes){fprintf(stderr,"%s TEST wrote output\n",ids[i]);failures++;}check(rsm_runtime_set_mode(&r,RSM_MODE_PROGRAM),RSM_STATUS_OK,"TEST PROGRAM");check(rsm_runtime_get_diagnostics(&r,&d),RSM_STATUS_OK,"lifecycle final");if(d.scan_count!=2u){fprintf(stderr,"%s expected exactly two scans\n",ids[i]);failures++;}rsm_runtime_deinit(&r);}
    printf("lifecycle matrix: PROGRAM→RUN→PROGRAM→TEST→PROGRAM for OTE/TON/CTU/CTD/ONS passed\n");return failures;
}

/* The source fixture is compiled by the Python image builder, then this native
 * test validates, sizes, loads, snapshots and independently scans it twice. */
static int high_state_contract(void) {
    const rsm_conformance_fixture_t *f=fixture("high-state-core-001");
    rsm_image_info_t info={0}; rsm_runtime_t a,b,short_arena; rsm_hal_t h=counted_hal();
    static uint8_t aa[65536],bb[65536],too_small[65536]; hal_counts_t ha={0},hb={0};
    rsm_runtime_diagnostics_t da={0},db={0}; rsm_snapshot_writer_t w; snapshot_t sa,sb;
    rsm_value_t va={0},vb={0}; size_t need=0u; int failures=0; unsigned alignment;
    if(!f)return 1;
    if(check(rsm_runtime_validate_image(f->image,f->image_size,&info),RSM_STATUS_OK,"high-state validate")||
       check(rsm_runtime_required_memory(f->image,f->image_size,&need),RSM_STATUS_OK,"high-state required memory"))return 1;
    if(info.instruction_count<300u||need==0u||need>sizeof aa){fputs("high-state fixture is not scalable\n",stderr);return 1;}
    if(check(rsm_runtime_init(&short_arena,too_small+1u,need-1u,&h,NULL),RSM_STATUS_OK,"high-state short init")||
       check(rsm_runtime_load_image(&short_arena,f->image,f->image_size),RSM_STATUS_BUFFER_TOO_SMALL,"high-state exact memory boundary"))return 1;
    rsm_runtime_deinit(&short_arena);
    for(alignment=0u;alignment<8u;alignment++){
        if(check(rsm_runtime_init(&short_arena,too_small+alignment,need,&h,NULL),RSM_STATUS_OK,"unaligned exact init")||
           check(rsm_runtime_load_image(&short_arena,f->image,f->image_size),RSM_STATUS_OK,"unaligned exact load")){fprintf(stderr,"unaligned exact arena offset %u failed\n",alignment);return 1;}
        rsm_runtime_deinit(&short_arena);
    }
    if(check(rsm_runtime_init(&a,aa,need,&h,&ha),RSM_STATUS_OK,"high-state init a")||
       check(rsm_runtime_init(&b,bb,need,&h,&hb),RSM_STATUS_OK,"high-state init b")||
       check(rsm_runtime_load_image(&a,f->image,f->image_size),RSM_STATUS_OK,"high-state load a")||
       check(rsm_runtime_load_image(&b,f->image,f->image_size),RSM_STATUS_OK,"high-state load b")||
       check(rsm_runtime_get_diagnostics(&a,&da),RSM_STATUS_OK,"high-state diagnostics a")||
       check(rsm_runtime_get_diagnostics(&b,&db),RSM_STATUS_OK,"high-state diagnostics b"))return 1;
    if(da.state_slot_count!=300u||db.state_slot_count!=300u){fputs("high-state state_slot_count is not exact\n",stderr);failures++;}
    check(rsm_runtime_set_mode(&a,RSM_MODE_RUN),RSM_STATUS_OK,"high-state run a");
    check(rsm_runtime_set_mode(&b,RSM_MODE_RUN),RSM_STATUS_OK,"high-state run b");
    ha.now=1000u; hb.now=1000u;
    check(rsm_runtime_scan(&a),RSM_STATUS_OK,"high-state scan a");
    check(rsm_runtime_scan(&b),RSM_STATUS_OK,"high-state scan b");
    va.type=RSM_TYPE_BOOL;va.value.boolean=RSM_TRUE;
    check(rsm_runtime_write_tag(&a,0u,&va),RSM_STATUS_OK,"high-state gate a");
    check(rsm_runtime_write_tag(&b,0u,&va),RSM_STATUS_OK,"high-state gate b");
    ha.now=2000u; hb.now=2000u;
    check(rsm_runtime_scan(&a),RSM_STATUS_OK,"high-state second scan a");
    check(rsm_runtime_scan(&b),RSM_STATUS_OK,"high-state second scan b");
    if(check(rsm_runtime_read_member(&a,1u,2u,&va),RSM_STATUS_OK,"high-state read a")||
       check(rsm_runtime_read_member(&b,300u,2u,&vb),RSM_STATUS_OK,"high-state read b")||
       va.value.dint!=1||vb.value.dint!=1){fprintf(stderr,"high-state independent scan values wrong: %d %d\n",va.value.dint,vb.value.dint);failures++;}
    memset(&w,0,sizeof w);w.value=snap_value;w.member=snap_member;w.state=snap_state;w.rung_power=snap_rung;
    memset(&sa,0,sizeof sa);memset(&sb,0,sizeof sb);w.context=&sa;
    if(check(rsm_runtime_snapshot(&a,&w),RSM_STATUS_OK,"high-state snapshot a"))return 1;
    w.context=&sb;if(check(rsm_runtime_snapshot(&b,&w),RSM_STATUS_OK,"high-state snapshot b"))return 1;
    if(sa.states!=300u||sb.states!=300u||sa.last_slot!=299u||sb.last_slot!=299u){fputs("high-state exact snapshot state count wrong\n",stderr);failures++;}
    if(check(rsm_runtime_get_diagnostics(&a,&da),RSM_STATUS_OK,"high-state post diagnostics a")||
       check(rsm_runtime_get_diagnostics(&b,&db),RSM_STATUS_OK,"high-state post diagnostics b")||da.scan_count!=2u||db.scan_count!=2u){fputs("high-state peer scan isolation failed\n",stderr);failures++;}
    rsm_runtime_deinit(&a);rsm_runtime_deinit(&b);rsm_runtime_deinit(&short_arena);
    printf("high-state generated image: 300 slots, exact memory, snapshots and two runtimes passed\n");
    return failures;
}

/* Slot identities are image IDs, not arena offsets: RES must find sparse slots. */
static int sparse_res_contract(void) {
    const rsm_conformance_fixture_t *f=fixture("ctu-core-001"); uint8_t image[65536],*code;
    rsm_runtime_t r; rsm_hal_t h=counted_hal(); hal_counts_t hc={0}; uint8_t arena[65536]; rsm_snapshot_writer_t w; snapshot_t s; rsm_value_t value; size_t n;
    if(!f)return 1;
    n=f->image_size;memcpy(image,f->image,n);code=section(image,8u);
    code[0]=RSM_OP_CTU;put32(code+8u,299u);code[13u]=RSM_TYPE_COUNTER;put32(code+16u,1u);
    instruction(code,1u)[0]=RSM_OP_RES;put32(instruction(code,1u)+8u,NONE);seal(image,n);
    if(check(rsm_runtime_validate_image(image,n,&(rsm_image_info_t){0}),RSM_STATUS_OK,"sparse RES validate")||
       check(rsm_runtime_init(&r,arena,sizeof arena,&h,&hc),RSM_STATUS_OK,"sparse RES init")||
       check(rsm_runtime_load_image(&r,image,n),RSM_STATUS_OK,"sparse RES load")||
       check(rsm_runtime_set_mode(&r,RSM_MODE_RUN),RSM_STATUS_OK,"sparse RES run")||
       check(rsm_runtime_scan(&r),RSM_STATUS_OK,"sparse RES scan")||
       check(rsm_runtime_read_member(&r,1u,2u,&value),RSM_STATUS_OK,"sparse RES counter"))return 1;
    memset(&w,0,sizeof w);memset(&s,0,sizeof s);w.context=&s;w.value=snap_value;w.member=snap_member;w.state=snap_state;
    if(check(rsm_runtime_snapshot(&r,&w),RSM_STATUS_OK,"sparse RES snapshot")||value.value.dint!=0||s.states!=1u||s.last_slot!=299u){fprintf(stderr,"sparse RES mapping failed: acc=%d states=%u slot=%u\n",value.value.dint,s.states,s.last_slot);rsm_runtime_deinit(&r);return 1;}
    rsm_runtime_deinit(&r);puts("sparse RES slot mapping passed");return 0;
}

/* Failed RUN/TEST unloads must retain their active image; PROGRAM unload is
 * followed by real invalid-state calls, a fresh reload, and a live peer. */
static int unload_reload_contract(void) {
    const rsm_conformance_fixture_t *f=fixture("unload-reload-core-001");
    rsm_runtime_t a,b; rsm_hal_t h=counted_hal(); uint8_t aa[65536],bb[65536];
    rsm_value_t value={0},peer_before={0},peer_after={0}; rsm_runtime_diagnostics_t diagnostics={0};
    int failures=0;
    if(!f)return 1;
    if(check(rsm_runtime_init(&a,aa,sizeof aa,&h,NULL),RSM_STATUS_OK,"unload init a")||
       check(rsm_runtime_init(&b,bb,sizeof bb,&h,NULL),RSM_STATUS_OK,"unload init b")||
       check(rsm_runtime_load_image(&a,f->image,f->image_size),RSM_STATUS_OK,"unload load a")||
       check(rsm_runtime_load_image(&b,f->image,f->image_size),RSM_STATUS_OK,"unload load b")||
       check(rsm_runtime_read_tag(&b,1u,&peer_before),RSM_STATUS_OK,"unload peer before"))return 1;
    if(check(rsm_runtime_set_mode(&a,RSM_MODE_RUN),RSM_STATUS_OK,"unload RUN")||
       check(rsm_runtime_unload_program(&a),RSM_STATUS_INVALID_STATE,"unload in RUN")||
       check(rsm_runtime_read_tag(&a,1u,&value),RSM_STATUS_OK,"RUN unload retained image"))failures++;
    if(check(rsm_runtime_set_mode(&a,RSM_MODE_PROGRAM),RSM_STATUS_OK,"unload PROGRAM")||
       check(rsm_runtime_set_mode(&a,RSM_MODE_TEST),RSM_STATUS_OK,"unload TEST")||
       check(rsm_runtime_unload_program(&a),RSM_STATUS_INVALID_STATE,"unload in TEST")||
       check(rsm_runtime_read_tag(&a,1u,&value),RSM_STATUS_OK,"TEST unload retained image"))failures++;
    if(check(rsm_runtime_set_mode(&a,RSM_MODE_PROGRAM),RSM_STATUS_OK,"unload final PROGRAM")||
       check(rsm_runtime_unload_program(&a),RSM_STATUS_OK,"unload in PROGRAM")||
       check(rsm_runtime_read_tag(&a,0u,&value),RSM_STATUS_INVALID_STATE,"unload read")||
       check(rsm_runtime_scan(&a),RSM_STATUS_INVALID_STATE,"unload scan")||
       check(rsm_runtime_get_diagnostics(&a,&diagnostics),RSM_STATUS_INVALID_STATE,"unload diagnostics")||
       check(rsm_runtime_read_tag(&b,1u,&peer_after),RSM_STATUS_OK,"unload peer after"))failures++;
    if(peer_before.type!=peer_after.type||peer_before.value.dint!=peer_after.value.dint){fputs("unload changed peer runtime\n",stderr);failures++;}
    if(check(rsm_runtime_load_image(&a,f->image,f->image_size),RSM_STATUS_OK,"unload reload")||
       check(rsm_runtime_get_diagnostics(&a,&diagnostics),RSM_STATUS_OK,"unload reload diagnostics")||
       check(rsm_runtime_read_tag(&a,1u,&value),RSM_STATUS_OK,"unload reload read"))failures++;
    if(diagnostics.scan_count!=0u||value.type!=RSM_TYPE_DINT||value.value.dint!=7){fputs("unload reload did not restore fresh fixture state\n",stderr);failures++;}
    rsm_runtime_deinit(&a);rsm_runtime_deinit(&b);
    puts("unload lifecycle: RUN/TEST refusal, PROGRAM detach, reload and peer isolation passed");
    return failures;
}

int main(void) { int failures=0; failures+=hostile_scale_contract();failures+=hostile_state_scale_contract();failures+=malformed_matrix();failures+=lifecycle_matrix();failures+=snapshots_are_immutable();failures+=high_state_contract();failures+=sparse_res_contract();failures+=unload_reload_contract();if(failures){fprintf(stderr,"runtime regressions: %d failures\n",failures);return 1;}puts("runtime validator, lifecycle and snapshot regressions passed");return 0;}
