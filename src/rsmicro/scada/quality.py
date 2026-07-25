from dataclasses import dataclass
from datetime import datetime, timezone
from enum import IntEnum, StrEnum

class QualityLevel(IntEnum):
 GOOD=0; UNCERTAIN=1; STALE=2; BAD=3
class QualityReason(StrEnum):
 GOOD_LIVE="GOOD_LIVE"; GOOD_FORCED="GOOD_FORCED"; GOOD_SUBSTITUTED="GOOD_SUBSTITUTED"
 UNCERTAIN_INITIALIZING="UNCERTAIN_INITIALIZING"; UNCERTAIN_PROGRAM_CHANGED="UNCERTAIN_PROGRAM_CHANGED"; UNCERTAIN_HOLD_LAST="UNCERTAIN_HOLD_LAST"
 BAD_CONFIGURATION="BAD_CONFIGURATION"; BAD_TYPE_MISMATCH="BAD_TYPE_MISMATCH"; BAD_CONTROLLER_FAULT="BAD_CONTROLLER_FAULT"; BAD_WRITE_REJECTED="BAD_WRITE_REJECTED"; BAD_MANIFEST_MISMATCH="BAD_MANIFEST_MISMATCH"
 STALE_CONTROLLER_TIMEOUT="STALE_CONTROLLER_TIMEOUT"; STALE_TAG_TIMEOUT="STALE_TAG_TIMEOUT"; STALE_CONSUMED_SOURCE="STALE_CONSUMED_SOURCE"
@dataclass(frozen=True, slots=True)
class Quality:
 level: QualityLevel; reason: QualityReason; timestamp: str; source: str; message: str|None=None
 @classmethod
 def now(cls, level, reason, source="broker", message=None):
  return cls(level, reason, datetime.now(timezone.utc).isoformat(), source, message)
 def to_dict(self): return {"level":self.level.name,"reason":self.reason.value,"timestamp":self.timestamp,"source":self.source,"message":self.message}
