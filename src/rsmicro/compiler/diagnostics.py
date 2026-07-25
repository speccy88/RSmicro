from dataclasses import dataclass,asdict
@dataclass(frozen=True)
class CompilerDiagnostic:
 severity:str; code:str; message:str; path:str=''
 def to_dict(self): return asdict(self)
