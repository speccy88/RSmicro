import shutil,subprocess
from pathlib import Path
from .discovery import library_filename
from .errors import NativeSimulationError

def build_native(build_dir="build",clean=False,configuration="Release",sanitize=False):
 if not shutil.which("cmake"): raise NativeSimulationError("CMake was not found on PATH")
 root=Path(__file__).resolve().parents[3]; out=Path(build_dir)
 if not out.is_absolute(): out=root/out
 if clean and out.exists(): shutil.rmtree(out)
 args=["cmake","-S",str(root),"-B",str(out),"-DRSM_BUILD_SHARED=ON",f"-DCMAKE_BUILD_TYPE={configuration}"]
 if sanitize: args.append("-DRSM_ENABLE_SANITIZERS=ON")
 subprocess.run(args,check=True); subprocess.run(["cmake","--build",str(out),"--config",configuration],check=True)
 hits=list(out.rglob(library_filename()))
 if not hits: raise NativeSimulationError("native build completed but the shared library was not found")
 return hits[0].resolve()
