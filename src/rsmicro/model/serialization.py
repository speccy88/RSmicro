import json,os,tempfile
from pathlib import Path
from .project import Project

def dumps_project(p): return json.dumps(p.to_dict(),indent=2,ensure_ascii=False)+"\n"
def save_project(p,path):
 target=Path(path); target.parent.mkdir(parents=True,exist_ok=True)
 fd,tmp=tempfile.mkstemp(prefix=f".{target.name}.",dir=target.parent)
 try:
  with os.fdopen(fd,"w",encoding="utf-8",newline="\n") as f: f.write(dumps_project(p)); f.flush(); os.fsync(f.fileno())
  os.replace(tmp,target)
 except BaseException:
  try: os.unlink(tmp)
  except FileNotFoundError: pass
  raise
def load_project(path): return Project.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
