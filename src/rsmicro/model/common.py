from __future__ import annotations
from typing import Any
from uuid import UUID
Metadata = dict[str, Any]
def require_uuid(value: str) -> str:
    UUID(value); return value
