from dataclasses import dataclass
import ctypes.util, os, platform
from pathlib import Path
from .errors import NativeLibraryNotFoundError

def library_filename(system=None):
    system=system or platform.system()
    return "rsmcore.dll" if system=="Windows" else "librsmcore.dylib" if system=="Darwin" else "librsmcore.so"

@dataclass(frozen=True)
class LibrarySearch:
    candidates: tuple[str,...]
    selected: str|None

def discover_library(explicit=None):
    name=library_filename(); root=Path(__file__).resolve().parents[3]
    raw=[]
    if explicit: raw.append(Path(explicit))
    if os.environ.get("RSMICRO_CORE_LIBRARY"): raw.append(Path(os.environ["RSMICRO_CORE_LIBRARY"]))
    raw += [root/"build"/"runtime"/"core"/name, Path(__file__).parent/"lib"/name]
    seen=[]
    for p in raw:
        q=str(p.expanduser().resolve())
        if q not in seen: seen.append(q)
        if Path(q).is_file(): return LibrarySearch(tuple(seen),q)
    found=ctypes.util.find_library("rsmcore")
    if found: return LibrarySearch(tuple([*seen,found]),found)
    raise NativeLibraryNotFoundError("RSmicro core library not found; build it with 'rsmicro native build' or set RSMICRO_CORE_LIBRARY",library_path=str(explicit) if explicit else None)
