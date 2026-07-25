import json
from pathlib import Path
from uuid import uuid4
import pytest
from rsmicro.cli import main
from rsmicro.migration import migrate_legacy
from rsmicro.model import *
from rsmicro.schemas import load_schema,validate_schema
ROOT=Path(__file__).parents[1]
def minimal(): return Project(str(uuid4()),"test")
def test_minimal_roundtrip_and_schema(tmp_path):
 p=minimal(); out=tmp_path/"p.rsmproj"; save_project(p,out)
 assert load_project(out).to_dict()==p.to_dict(); assert out.read_bytes().endswith(b"\n"); assert not validate_schema(p.to_dict())
 assert load_schema()["$schema"].endswith("2020-12/schema")
def test_full_model_nested_branch_and_validation():
 ids=[str(uuid4()) for _ in range(12)]; tag=Tag(ids[1],"timer",TagType.TIMER,preset=10)
 ins=Instruction(ids[2],"XIC",[TagOperand(ids[1],"DN")]); branch=Branch([[ins],[Branch([[Instruction(ids[3],"OTE",[TagOperand(ids[1],"DN")])],[Instruction(ids[4],"XIO",[TagOperand(ids[1],"TT")])]])]])
 rung=Rung(ids[5],[branch],"comment"); routine=Routine(ids[6],"Main",[rung]); prog=Program(ids[7],"Program",[routine]); c=Controller(ids[8],"PLC",tags=[tag],programs=[prog]); p=Project(ids[0],"full",controllers=[c])
 assert not [d for d in validate_project(p) if d.severity.value=="ERROR"]
def test_all_tag_types():
 for t in TagType: assert Tag(str(uuid4()),t.value,t,preset=0 if t in {TagType.TIMER,TagType.COUNTER} else None).data_type==t
def test_migration_all_examples_is_deterministic_and_valid(tmp_path):
 sources=sorted((ROOT/"examples").glob("*.json")); assert len(sources)==7
 for src in sources:
  a=tmp_path/(src.stem+"a"); b=tmp_path/(src.stem+"b"); original=src.read_bytes(); pa,ra=migrate_legacy(src,a); pb,rb=migrate_legacy(src,b)
  assert a.read_bytes()==b.read_bytes(); assert pa.project_id==pb.project_id; assert src.read_bytes()==original
  assert not [d for d in validate_project(pa) if d.severity.value=="ERROR"]
  assert a.read_bytes()==(ROOT/"examples/migrated"/(src.stem+".rsmproj")).read_bytes()
def test_cli(tmp_path,capsys):
 src=ROOT/"examples/circuitpython_button_led.json"; out=tmp_path/"x.rsmproj"
 assert main(["migrate-v1",str(src),"--output",str(out)])==0
 assert main(["migrate-v1",str(src),"--output",str(out)])==2
 assert main(["validate",str(out),"--format","json"])==0
 assert main(["show-project",str(out)])==0; assert "Controllers:" in capsys.readouterr().out
def test_malformed_and_unsupported(tmp_path):
 p=tmp_path/"bad"; p.write_text("{"); assert main(["validate",str(p)])==1
 x=minimal(); x.format_version=2; save_project(x,p); assert any(d.code=="FORMAT_VERSION_UNSUPPORTED" for d in validate_project(x))
def test_unknown_instruction_reported(tmp_path):
 src=tmp_path/"legacy.json"; src.write_text(json.dumps({"name":"x","rungs":[{"elements":[{"op":"MYSTERY","tag":"x"}]}]})); _,r=migrate_legacy(src); assert any(x["code"]=="INSTRUCTION_UNSUPPORTED" for x in r.errors)
