from __future__ import annotations
import shutil, tempfile
from pathlib import Path
from rsmicro.model import load_project, save_project

class ProjectSession:
 """Qt-independent project lifecycle and recovery service."""
 def __init__(self, recovery_root: Path | None = None):
  self.project=None; self.path:Path|None=None; self.dirty=False
  self.recovery_root=recovery_root or Path(tempfile.gettempdir())/"rsmicro-studio-recovery"
 def open(self,path): self.project=load_project(path); self.path=Path(path); self.dirty=False; return self.project
 def save(self,path=None):
  if self.project is None: raise RuntimeError("no project is open")
  target=Path(path) if path else self.path
  if target is None: raise ValueError("a destination is required")
  save_project(self.project,target); self.path=target; self.dirty=False; self.discard_recovery()
 def mark_dirty(self): self.dirty=True
 @property
 def recovery_path(self): return self.recovery_root/f"{self.project.project_id}.rsmproj" if self.project else None
 def autosave(self):
  if not self.dirty or self.project is None: return None
  self.recovery_root.mkdir(parents=True,exist_ok=True); save_project(self.project,self.recovery_path); return self.recovery_path
 def discard_recovery(self):
  if self.recovery_path: self.recovery_path.unlink(missing_ok=True)
