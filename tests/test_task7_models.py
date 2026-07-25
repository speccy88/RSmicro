from pathlib import Path
from rsmicro.model import load_project
from rsmicro.scada_screen import Screen,ScreenObject,validate_screen,WIDGET_TYPES
from rsmicro.studio.session import ProjectSession

def test_all_widget_types_are_declarative():
 s=Screen('s','screen',objects=[ScreenObject(str(i),kind,{'x':0,'y':0,'width':10,'height':10}) for i,kind in enumerate(sorted(WIDGET_TYPES))])
 assert not validate_screen(s)
 assert s.to_dict()['format']=='rsmicro-scada-screen'

def test_invalid_action_and_duplicate_uuid():
 o=ScreenObject('same','pushbutton',{'width':10,'height':10},action={'type':'EXEC'})
 assert len(validate_screen(Screen('s','x',objects=[o,o])))==3

def test_project_session_recovery(tmp_path):
 source=Path('examples/compiler_demo/project.rsmproj'); session=ProjectSession(tmp_path/'recovery'); session.open(source); session.mark_dirty()
 recovery=session.autosave(); assert recovery.exists(); assert load_project(recovery).project_id==session.project.project_id
 target=tmp_path/'saved.rsmproj'; session.save(target); assert target.exists(); assert not recovery.exists(); assert not session.dirty

def test_integrated_demo_screens_are_valid():
 project=load_project('examples/multi_node_scada_demo/project.rsmproj'); root=Path('examples/multi_node_scada_demo')
 tags={t.tag_id for c in project.controllers for t in c.tags}
 for ref in project.scada.screens:
  import json
  screen=Screen.from_dict(json.loads((root/ref).read_text()))
  assert not validate_screen(screen,tags)
