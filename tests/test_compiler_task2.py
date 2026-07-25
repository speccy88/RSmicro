import json,subprocess,sys
from pathlib import Path
import pytest
from rsmicro.model import load_project
from rsmicro.compiler import compile_project,inspect_image
from rsmicro.compiler.profile import load_profile,load_instruction,profile_root
from rsmicro.compiler.generated_opcodes import OPCODES,ALIASES
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
 info=inspect_image(a.image_bytes); assert info['crc_valid'] and info['instruction_count']==a.manifest['instruction_count']; assert info['tag_count']==9
@pytest.mark.parametrize('mutator,message',[
 (lambda x: b'BAD!'+x[4:],'wrong magic'),(lambda x:x[:10],'truncated header'),(lambda x:x[:-1],'truncated or oversized image')])
def test_reject_bad_images(mutator,message):
 p=load_project(ROOT/'examples/compiler_demo/project.rsmproj'); raw=compile_project(p,'controller-a').image_bytes
 with pytest.raises(ValueError,match=message): inspect_image(mutator(raw))
def test_generated_current():
 r=subprocess.run([sys.executable,str(ROOT/'tools/generate_instruction_registry.py'),'--check'],cwd=ROOT); assert r.returncode==0
def test_fixture_coverage():
 required={'prescan','false_scan','true_scan','repeated_true','true_to_false','false_to_true','postscan','boundary','force','invalid_operand','multiple_instances','multiple_rungs'}
 fs=list((profile_root()/'conformance').glob('*.json')); assert len(fs)==24
 for f in fs: assert required <= set(json.loads(f.read_text())['coverage'])
