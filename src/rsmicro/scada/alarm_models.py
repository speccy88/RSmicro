from dataclasses import dataclass
from enum import StrEnum
from typing import Any
class AlarmCondition(StrEnum): BOOL_TRUE="BOOL_TRUE"; BOOL_FALSE="BOOL_FALSE"; HIGH="HIGH"; HIGH_HIGH="HIGH_HIGH"; LOW="LOW"; LOW_LOW="LOW_LOW"; BAD_QUALITY="BAD_QUALITY"; STALE_QUALITY="STALE_QUALITY"
class AlarmPriority(StrEnum): LOW="LOW"; MEDIUM="MEDIUM"; HIGH="HIGH"; CRITICAL="CRITICAL"
@dataclass(slots=True)
class AlarmDefinition:
 alarm_id:str; name:str; source_tag_id:str; condition:AlarmCondition; threshold:Any=None; priority:AlarmPriority=AlarmPriority.MEDIUM; message:str=""; enabled:bool=True; delay_on_ms:int=0; delay_off_ms:int=0; hysteresis:float=0; acknowledgement_required:bool=True; latching:bool=False; description:str=""
