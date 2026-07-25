"""Versioned, deterministic and non-executable SCADA screen definitions."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any

WIDGET_TYPES = frozenset({"label", "boolean_indicator", "pushbutton", "numeric_display",
 "numeric_input", "bar", "gauge", "trend", "alarm_banner", "connection_indicator",
 "force_indicator", "navigation_button"})
ACTIONS = frozenset({"WRITE_TRUE", "WRITE_FALSE", "TOGGLE", "MOMENTARY", "SET_VALUE", "NAVIGATE"})

@dataclass(slots=True)
class ScreenObject:
 object_id: str
 type: str
 geometry: dict[str, float]
 properties: dict[str, Any] = field(default_factory=dict)
 binding: dict[str, Any] = field(default_factory=dict)
 style: dict[str, Any] = field(default_factory=dict)
 action: dict[str, Any] = field(default_factory=dict)
 visible: bool = True
 locked: bool = False
 z_order: int = 0
 metadata: dict[str, Any] = field(default_factory=dict)
 def to_dict(self):
  return {"object_id":self.object_id,"type":self.type,"geometry":self.geometry,"properties":self.properties,
   "binding":self.binding,"style":self.style,"action":self.action,"visible":self.visible,"locked":self.locked,
   "z_order":self.z_order,"metadata":self.metadata}

@dataclass(slots=True)
class Screen:
 screen_id: str
 name: str
 width: int = 1280
 height: int = 720
 description: str = ""
 background: str = "#f0f0f0"
 scaling_policy: str = "fit"
 objects: list[ScreenObject] = field(default_factory=list)
 layers: list[dict[str, Any]] = field(default_factory=list)
 metadata: dict[str, Any] = field(default_factory=dict)
 format_version: int = 1
 def to_dict(self):
  return {"format":"rsmicro-scada-screen","format_version":self.format_version,"screen_id":self.screen_id,
   "name":self.name,"description":self.description,"width":self.width,"height":self.height,
   "background":self.background,"scaling_policy":self.scaling_policy,"objects":[o.to_dict() for o in self.objects],
   "layers":self.layers,"metadata":self.metadata}
 @classmethod
 def from_dict(cls, value):
  objects=[ScreenObject(**{k:v for k,v in o.items() if k in ScreenObject.__dataclass_fields__}) for o in value.get("objects",[])]
  return cls(value["screen_id"],value["name"],value.get("width",1280),value.get("height",720),
   value.get("description",""),value.get("background","#f0f0f0"),value.get("scaling_policy","fit"),objects,
   list(value.get("layers",[])),dict(value.get("metadata",{})),value.get("format_version",1))

def validate_screen(screen: Screen, tag_ids: set[str] | None = None) -> list[str]:
 errors=[]; seen=set(); tag_ids=tag_ids or set()
 if screen.width <= 0 or screen.height <= 0: errors.append("screen dimensions must be positive")
 for obj in screen.objects:
  if obj.object_id in seen: errors.append(f"duplicate object UUID: {obj.object_id}")
  seen.add(obj.object_id)
  if obj.type not in WIDGET_TYPES: errors.append(f"unsupported widget type: {obj.type}")
  if any(float(obj.geometry.get(k,0)) < 0 for k in ("width","height")): errors.append(f"invalid geometry: {obj.object_id}")
  tag_id=obj.binding.get("tag_uuid")
  if tag_id and tag_ids and tag_id not in tag_ids: errors.append(f"unknown tag UUID: {tag_id}")
  if obj.action and obj.action.get("type") not in ACTIONS: errors.append(f"unsupported action: {obj.action.get('type')}")
 return errors
