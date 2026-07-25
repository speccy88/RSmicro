import json,subprocess,sys
from pathlib import Path
import pytest
from rsmicro.model import load_project
from rsmicro.compiler import compile_project,inspect_image
from rsmicro.compiler.api import CompileOptions
from rsmicro.compiler.image import VERSION as IMAGE_FORMAT_VERSION
from rsmicro.compiler.profile import load_profile,load_instruction,profile_root
from rsmicro.compiler.generated_opcodes import OPCODES,ALIASES,INSTRUCTION_ABI,PROFILE_VERSION
ROOT=Path(__file__).parents[1]
def test_profile_complete_unique_and_fixtures():
 p=load_profile(); required='XIC XIO OTE OTL OTU ONS TON CTU CTD RES EQ NE GT GE LT LE MOV CLR ADD SUB MUL DIV NEG ABS'.split()
 assert list(OPCODES)==required; assert len(set(OPCODES.values()))==len(required); assert set(p['data_types'])=={'BOOL','DINT','REAL','TIMER','COUNTER'}
 assert ALIASES=={'GTE':'GE','GEQ':'GE','LTE':'LE','LEQ':'LE'}
 for m in required:
  s=load_instruction(m); assert s['fixtures'] and (profile_root()/s['fixtures'][0]).exists(); assert s['references'] and (profile_root()/s['references'][0]).exists()
def test_compile_deterministic_and_inspect():
 p=load_project(ROOT/'examples/compiler_demo/project.rsmproj'); a=compile_project(p,'controller-a'); b=compile_project(p,'11111111-1111-4111-8111-111111111111')
 assert a.success and b.success; assert a.image_bytes==b.image_bytes; assert a.manifest==b.manifest; assert a.debug_map==b.debug_map
 assert a.manifest['profile_version']==PROFILE_VERSION
 assert a.manifest['instruction_abi']==INSTRUCTION_ABI
 assert a.manifest['image_format']=='.'.join(map(str,IMAGE_FORMAT_VERSION))
 info=inspect_image(a.image_bytes); assert info['crc_valid'] and info['instruction_count']==a.manifest['instruction_count']; assert info['tag_count']==9
@pytest.mark.parametrize('mutator,message',[
 (lambda x: b'BAD!'+x[4:],'wrong magic'),(lambda x:x[:10],'truncated header'),(lambda x:x[:-1],'truncated or oversized image')])
def test_reject_bad_images(mutator,message):
 p=load_project(ROOT/'examples/compiler_demo/project.rsmproj'); raw=compile_project(p,'controller-a').image_bytes
 with pytest.raises(ValueError,match=message): inspect_image(mutator(raw))
def test_generated_current():
 r=subprocess.run([sys.executable,str(ROOT/'tools/generate_instruction_registry.py'),'--check'],cwd=ROOT); assert r.returncode==0
def test_semantic_fixture_schema():
 required={'id','profile','instruction','schema','tags','program','steps'}
 fs=list((profile_root()/'conformance').glob('*.json')); assert len(fs)>=26
 for f in fs:
  fixture=json.loads(f.read_text()); assert required <= set(fixture)
  assert fixture['tags'] and fixture['program'] and fixture['steps']
  times=[s.get('time_us',s.get('time_ms',0)*1000) for s in fixture['steps']]
  assert fixture.get('allow_clock_wrap',False) or times==sorted(times)
  for step in fixture['steps']:
   assert 'operation' in step
   values=step.get('assert',step.get('assertions',[step['expect']] if 'expect' in step else []))
   observable_fields={'status','mode','diagnostics','fault','output_writes','forces','instruction_states','rung_powers','write_trace'}
   assert values or observable_fields & set(step), f'{f.name}: step has no observable assertion: {step}'
   for value in values: assert {'tag','type','value'} <= set(value)

def _canonical_branch_project():
 """A source-model-only matrix; no IR objects or bytecode are constructed here."""
 ids={name:f'00000000-0000-4000-8000-{n:012d}' for n,name in enumerate(
  ('A','B','C','PRE','POST','LANE_A','LANE_B','BRANCH_OUT','THREE_A','THREE_B','THREE_C','NESTED_OUT','MULTI_OUT','ONS_ONE','ONS_TWO','TIMER','COUNTER'),1)}
 def tag(name,typ='BOOL',initial=False):
  d={'tag_id':ids[name],'name':name,'data_type':typ,'initial_value':initial}
  return d
 tags=[tag(x) for x in ('A','B','C','PRE','POST','LANE_A','LANE_B','BRANCH_OUT','THREE_A','THREE_B','THREE_C','NESTED_OUT','MULTI_OUT','ONS_ONE','ONS_TWO')]+[tag('TIMER','TIMER',5),tag('COUNTER','COUNTER',2)]
 serial=0
 def ins(m,*ops):
  nonlocal serial
  serial+=1
  return {'node_type':'instruction','instruction_id':f'10000000-0000-4000-8000-{serial:012d}','mnemonic':m,'operands':[{'kind':'tag','tag_id':ids[x]} if isinstance(x,str) else {'kind':'literal','value':x} for x in ops],'metadata':{}}
 def branch(*lanes): return {'node_type':'branch','lanes':[list(x) for x in lanes],'metadata':{}}
 rungs=[
  [ins('XIC','PRE'),branch([ins('XIC','A'),ins('OTE','LANE_A')],[ins('XIC','B'),ins('OTE','LANE_B')]),ins('XIC','POST'),ins('OTE','BRANCH_OUT')],
  [branch([ins('XIC','A'),ins('OTE','THREE_A')],[ins('XIC','B'),ins('OTE','THREE_B')],[ins('XIO','C'),ins('OTE','THREE_C')])],
  [branch([ins('XIC','A'),branch([ins('XIC','B')],[ins('XIC','C')])],[ins('XIO','C')]),ins('OTE','NESTED_OUT')],
  [branch([ins('XIC','A')],[ins('XIC','B')]),branch([ins('XIC','C')],[ins('XIO','C')]),ins('OTE','MULTI_OUT')],
  [ins('XIC','A'),ins('ONS'),ins('OTE','ONS_ONE')],
  [ins('XIC','B'),ins('ONS'),ins('OTE','ONS_TWO')],
  [ins('XIC','A'),ins('TON','TIMER')],
  [ins('XIC','B'),ins('CTU','COUNTER')],
 ]
 device={'device_id':'io','driver_type':'test','endpoints':[]}
 bindings=[]
 for name in ('A','B','C','PRE','POST'):
  endpoint=f'in-{name}'; device['endpoints'].append({'endpoint_id':endpoint,'direction':'input','data_type':'BOOL','address':name}); bindings.append({'binding_id':f'b-{name}','tag_id':ids[name],'device_id':'io','endpoint_id':endpoint})
 for name in ('LANE_A','LANE_B','BRANCH_OUT','THREE_A','THREE_B','THREE_C','NESTED_OUT','MULTI_OUT','ONS_ONE','ONS_TWO'):
  endpoint=f'out-{name}'; device['endpoints'].append({'endpoint_id':endpoint,'direction':'output','data_type':'BOOL','address':name}); bindings.append({'binding_id':f'b-{name}','tag_id':ids[name],'device_id':'io','endpoint_id':endpoint})
 controller={'controller_id':'20000000-0000-4000-8000-000000000001','name':'canonical-branch-controller','compatibility_profile':'RSM-LOGIX-CORE-1','tags':tags,'programs':[{'program_id':'30000000-0000-4000-8000-000000000001','name':'Main','routines':[{'routine_id':'40000000-0000-4000-8000-000000000001','name':'MainRoutine','rungs':[{'rung_id':f'50000000-0000-4000-8000-{n:012d}','nodes':nodes} for n,nodes in enumerate(rungs,1)]}]}]}
 return {'format':'rsmicro-project','format_version':1,'project_id':'60000000-0000-4000-8000-000000000001','name':'canonical-branch-matrix','controllers':[controller],'deployments':[{'deployment_id':'70000000-0000-4000-8000-000000000001','name':'native','controller_id':controller['controller_id'],'target_platform':'test','devices':[device],'bindings':bindings}]}

def test_canonical_project_compiles_to_rsm_and_runs_full_state_in_fresh_c_core(tmp_path):
 project_path=tmp_path/'canonical-branch-matrix.rsmproj'; project_path.write_text(json.dumps(_canonical_branch_project()))
 project=load_project(project_path)
 normal=compile_project(project,'canonical-branch-controller',deployment_id='native')
 stripped=compile_project(project,'canonical-branch-controller',deployment_id='native',options=CompileOptions(strip_debug=True))
 assert normal.success and stripped.success and normal.image_bytes != stripped.image_bytes
 assert normal.manifest['profile_version']==PROFILE_VERSION and normal.manifest['instruction_abi']==INSTRUCTION_ABI and normal.manifest['image_format']=='.'.join(map(str,IMAGE_FORMAT_VERSION))
 assert normal.debug_map['rungs'] and normal.debug_map['instructions'] and stripped.debug_map=={}
 assert {x['id'] for x in normal.debug_map['rungs']} == {x['id'] for x in normal.ir.rungs}
 assert {i.mnemonic for i in normal.ir.instructions} >= {'BRANCH_BEGIN','BRANCH_LANE_BEGIN','BRANCH_LANE_END','BRANCH_END'}
 hidden=[t for t in normal.ir.tags if t.name.startswith('__rsm_ons_storage_')]
 assert len(hidden)==2 and len({t.uuid for t in hidden})==2 and all(t.type=='BOOL' and t.storage=='INTERNAL' for t in hidden)
 assert [i.operands[0].value for i in normal.ir.instructions if i.mnemonic=='ONS']==[hidden[0].id,hidden[1].id]
 image=tmp_path/'canonical.rsm'; image.write_bytes(normal.image_bytes)
 source=tmp_path/'full_state.c'
 source.write_text(r'''#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "rsmicro/rsm_runtime.h"
enum { A,B,C,PRE,POST,LANE_A,LANE_B,BRANCH_OUT,THREE_A,THREE_B,THREE_C,NESTED_OUT,MULTI_OUT,ONS_ONE,ONS_TWO,TIMER,COUNTER,HIDDEN_A,HIDDEN_B,TAGS };
typedef struct { uint64_t now; rsm_bool_t in[5]; unsigned reads,writes; uint32_t read_order[64],write_order[128]; } hal_t;
typedef struct { rsm_value_t logical[TAGS],effective[TAGS],member[TAGS][10]; rsm_bool_t forced[TAGS],rung[8]; unsigned values,members,rungs,states; rsm_runtime_diagnostics_t diag; uint8_t mode; } snap_t;
static int bad(const char *s){fputs(s,stderr);fputc('\n',stderr);return 1;}
static uint64_t tick(void *p){return ((hal_t*)p)->now;}
static rsm_status_t input(void *p,uint32_t id,rsm_value_t *v){hal_t*h=p;if(id>=5)return RSM_STATUS_HAL_ERROR;h->read_order[h->reads++]=id;v->type=RSM_TYPE_BOOL;v->value.boolean=h->in[id];return RSM_STATUS_OK;}
static rsm_status_t output(void*p,uint32_t id,const rsm_value_t*v){hal_t*h=p;(void)v;h->write_order[h->writes++]=id;return RSM_STATUS_OK;}
static rsm_status_t sv(void*p,rsm_tag_id_t id,const rsm_value_t*l,const rsm_value_t*e,rsm_bool_t f){snap_t*s=p;if(id>=TAGS)return RSM_STATUS_HAL_ERROR;s->logical[id]=*l;s->effective[id]=*e;s->forced[id]=f;s->values++;return RSM_STATUS_OK;}
static rsm_status_t sm(void*p,rsm_tag_id_t id,rsm_member_id_t m,const rsm_value_t*v){snap_t*s=p;if(id>=TAGS||m>=10)return RSM_STATUS_HAL_ERROR;s->member[id][m]=*v;s->members++;return RSM_STATUS_OK;}
static rsm_status_t ss(void*p,uint8_t mode,const rsm_runtime_diagnostics_t*d,const rsm_fault_t*f,uint32_t slot,uint8_t edge,uint8_t valid,uint64_t time){snap_t*s=p;(void)f;(void)slot;(void)edge;(void)valid;(void)time;s->mode=mode;s->diag=*d;s->states++;return RSM_STATUS_OK;}
static rsm_status_t sr(void*p,uint32_t id,rsm_bool_t power){snap_t*s=p;if(id>=8)return RSM_STATUS_HAL_ERROR;s->rung[id]=power;s->rungs++;return RSM_STATUS_OK;}
static int snapshot(rsm_runtime_t*r,snap_t*s){rsm_snapshot_writer_t w;memset(s,0,sizeof *s);memset(&w,0,sizeof w);w.context=s;w.value=sv;w.member=sm;w.state=ss;w.rung_power=sr;return rsm_runtime_snapshot(r,&w)==RSM_STATUS_OK?0:bad("snapshot");}
static int scan(rsm_runtime_t*r,hal_t*h,int a,int b,int c,int expect_branch,int expect_three_c,int expect_nested,int expect_multi,int expect_ons1,int expect_ons2){snap_t s;unsigned i;h->in[A]=(rsm_bool_t)a;h->in[B]=(rsm_bool_t)b;h->in[C]=(rsm_bool_t)c;h->in[PRE]=h->in[POST]=1;h->now+=1000;h->reads=h->writes=0;if(rsm_runtime_clear_write_trace(r)||rsm_runtime_scan(r)||snapshot(r,&s))return bad("scan status");if(s.values!=17u||s.members!=12u||s.rungs!=8u||s.mode!=RSM_MODE_RUN||s.diag.scan_count==0)return bad("incomplete snapshot");for(i=0;i<5;i++)if(h->read_order[i]!=i)return bad("HAL input order");for(i=0;i<10;i++)if(h->write_order[i]!=i+5u)return bad("HAL output order");if(s.logical[LANE_A].value.boolean!=(unsigned)a||s.logical[LANE_B].value.boolean!=(unsigned)b||s.logical[BRANCH_OUT].value.boolean!=(unsigned)expect_branch||s.logical[THREE_A].value.boolean!=(unsigned)a||s.logical[THREE_B].value.boolean!=(unsigned)b||s.logical[THREE_C].value.boolean!=(unsigned)expect_three_c||s.logical[NESTED_OUT].value.boolean!=(unsigned)expect_nested||s.logical[MULTI_OUT].value.boolean!=(unsigned)expect_multi||s.logical[ONS_ONE].value.boolean!=(unsigned)expect_ons1||s.logical[ONS_TWO].value.boolean!=(unsigned)expect_ons2)return bad("branch/output matrix");return 0;}
int main(int n,char **v){FILE*f;long z;uint8_t*image,arena[65536],arena_a[65536],arena_b[65536];rsm_runtime_t r,ra,rb;rsm_hal_t h;hal_t hc,ha,hb; snap_t s,sa,sb;rsm_value_t force; rsm_runtime_write_trace_entry_t trace[64];size_t count;unsigned i;const uint32_t want[]={LANE_A,LANE_B,BRANCH_OUT,THREE_A,THREE_B,THREE_C,NESTED_OUT,MULTI_OUT,HIDDEN_A,ONS_ONE,HIDDEN_B,ONS_TWO};const rsm_bool_t final_bool[]={0,0,1,1,1,0,0,0,0,0,0,0,0,0,0};
 if(n!=2)return bad("argument");
 memset(&hc,0,sizeof hc); memset(&h,0,sizeof h); h.monotonic_time_us=tick; h.read_input=input; h.write_output=output;
 f=fopen(v[1],"rb"); if(!f)return bad("open"); fseek(f,0,SEEK_END); z=ftell(f); rewind(f); image=malloc((size_t)z);
 if(!image||fread(image,1,(size_t)z,f)!=(size_t)z)return bad("read");
 fclose(f);
 /* Load the same canonical branch image into two native runtimes.  Drive and
  * scan them independently, then prove their branch outputs and scan state do
  * not leak across instances. */
 memset(&ha,0,sizeof ha); memset(&hb,0,sizeof hb);
 if(rsm_runtime_init(&ra,arena_a,sizeof arena_a,&h,&ha)||rsm_runtime_init(&rb,arena_b,sizeof arena_b,&h,&hb)||rsm_runtime_load_image(&ra,image,(size_t)z)||rsm_runtime_load_image(&rb,image,(size_t)z)||rsm_runtime_set_mode(&ra,RSM_MODE_RUN)||rsm_runtime_set_mode(&rb,RSM_MODE_RUN))return bad("dual runtime load");
 if(scan(&ra,&ha,1,0,1,1,0,1,1,0,0)||scan(&rb,&hb,0,0,1,0,0,0,0,0,0)||snapshot(&ra,&sa)||snapshot(&rb,&sb))return bad("dual runtime scan");
 if(!sa.logical[BRANCH_OUT].value.boolean||sb.logical[BRANCH_OUT].value.boolean||sa.diag.scan_count!=1u||sb.diag.scan_count!=1u)return bad("dual runtime distinct outputs");
 if(scan(&ra,&ha,0,0,1,0,0,0,0,0,0)||scan(&ra,&ha,1,0,1,1,0,1,1,1,0)||snapshot(&ra,&sa)||snapshot(&rb,&sb))return bad("dual runtime independent rescan");
 if(!sa.logical[BRANCH_OUT].value.boolean||sb.logical[BRANCH_OUT].value.boolean||sa.diag.scan_count!=3u||sb.diag.scan_count!=1u)return bad("dual runtime state isolation");
 rsm_runtime_deinit(&ra); rsm_runtime_deinit(&rb);
 if(rsm_runtime_init(&r,arena,sizeof arena,&h,&hc)||rsm_runtime_load_image(&r,image,(size_t)z)||rsm_runtime_set_mode(&r,RSM_MODE_RUN))return bad("load/lifecycle");
 /* A-only, B-only, neither, then an XIO-true three-lane/nested case. */
 if(scan(&r,&hc,1,0,1,1,0,1,1,0,0)||scan(&r,&hc,0,1,1,1,0,0,1,0,1)||scan(&r,&hc,0,0,1,0,0,0,0,0,0)||scan(&r,&hc,0,0,0,0,1,1,0,0,0))return 1;
 /* Return to C=true/neither and prove force overlay versus backing write trace. */
 if(scan(&r,&hc,0,0,1,0,0,0,0,0,0))return 1;
 force.type=RSM_TYPE_BOOL; force.value.boolean=1;
 if(rsm_runtime_force_tag(&r,BRANCH_OUT,&force)||rsm_runtime_clear_write_trace(&r))return bad("force setup");
 hc.now+=1000;
 if(rsm_runtime_scan(&r)||snapshot(&r,&s)||rsm_runtime_get_write_trace(&r,trace,64,&count))return bad("force scan");
 if(!s.forced[BRANCH_OUT]||s.logical[BRANCH_OUT].value.boolean||!s.effective[BRANCH_OUT].value.boolean||s.logical[HIDDEN_A].value.boolean||s.logical[HIDDEN_B].value.boolean)return bad("force/logical/effective");
 for(i=0;i<15u;i++)if(s.logical[i].value.boolean!=final_bool[i])return bad("complete final scalar state");
 if(count!=12u) return bad("write trace length");
 for(i=0;i<count;i++)if(trace[i].tag!=want[i])return bad("backing write trace order");
 if(s.member[TIMER][1].value.dint!=5||s.member[TIMER][2].value.dint||s.member[TIMER][3].value.boolean||s.member[TIMER][4].value.boolean||s.member[TIMER][5].value.boolean||s.member[COUNTER][1].value.dint!=2||s.member[COUNTER][2].value.dint!=1||s.member[COUNTER][5].value.boolean||s.member[COUNTER][6].value.boolean||s.member[COUNTER][7].value.boolean)return bad("composite final state");
 for(i=0;i<8;i++)if(s.rung[i])return bad("rung power");
 if(rsm_runtime_set_mode(&r,RSM_MODE_PROGRAM)||rsm_runtime_set_mode(&r,RSM_MODE_TEST))return bad("mode transition");
 hc.writes=0; hc.now+=1000;
 if(rsm_runtime_scan(&r)||hc.writes||snapshot(&r,&s)||s.mode!=RSM_MODE_TEST||s.diag.scan_count!=7u)return bad("TEST lifecycle");
 if(rsm_runtime_set_mode(&r,RSM_MODE_PROGRAM)||rsm_runtime_clear_force(&r,BRANCH_OUT))return bad("postscan/clear force");
 rsm_runtime_deinit(&r); free(image); return 0;
}
''')
 build=tmp_path/'fresh-core'
 harness=ROOT/'tests/cmake/compiler_native_harness'
 subprocess.run([
  'cmake','-S',str(harness),'-B',str(build),
  f'-DRSMICRO_SOURCE_DIR={ROOT}',f'-DRSM_HARNESS_SOURCE={source}',f'-DRSM_IMAGE={image}',
  '-DRSM_ENABLE_STRICT_WARNINGS=ON',
 ],check=True)
 subprocess.run(['cmake','--build',str(build),'--target','canonical_native_harness','--parallel'],check=True)
 subprocess.run(['ctest','--test-dir',str(build),'--output-on-failure'],check=True)
