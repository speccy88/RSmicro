from dataclasses import dataclass
from typing import Any
@dataclass(slots=True)
class CommandRecord:
 command_id:str; requester:str; requested_value:Any; request_time:str; controller_request_id:int|None=None; applied_scan_number:int|None=None; completion_time:str|None=None; success:bool|None=None
