from __future__ import annotations
from dataclasses import asdict, dataclass
from enum import StrEnum

class Severity(StrEnum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"

@dataclass(slots=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str
    source_file: str | None = None
    path: str | None = None
    project_id: str | None = None
    controller_id: str | None = None
    program_id: str | None = None
    routine_id: str | None = None
    rung_id: str | None = None
    instruction_id: str | None = None
    suggestion: str | None = None
    def to_dict(self) -> dict[str, object]:
        return {k: (str(v) if isinstance(v, Severity) else v) for k, v in asdict(self).items() if v is not None}
