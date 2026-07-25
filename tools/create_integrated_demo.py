#!/usr/bin/env python3
"""Recreate the checked-in Task 8 demonstration using stable UUIDv5 identifiers."""
from __future__ import annotations
import json
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "examples" / "integrated_demo"
NS = UUID("d52fa76c-b155-4a71-a663-b8dcfc8f69d1")
uid = lambda value: str(uuid5(NS, value))

def tag(controller: str, name: str, typ: str, value=False, preset=None, writable=True, **metadata):
    return {"tag_id":uid(f"{controller}/tag/{name}"),"name":name,"description":"Integrated demonstration tag","data_type":typ,
            "initial_value":None if typ in ("TIMER","COUNTER") else value,"preset":preset,"retentive":False,"writable":writable,
            "access":{"forceable":metadata.pop("forceable",False)},"engineering_unit":metadata.pop("unit",None),"minimum":None,"maximum":None,
            "scada_visible":True,"metadata":metadata}

def operand(controller: str, value, member=None):
    if isinstance(value, str):
        result={"kind":"tag_member" if member else "tag","tag_id":uid(f"{controller}/tag/{value}")}
        if member: result["member"]=member
        return result
    return {"kind":"literal","value":value}

def ins(controller: str, rung: str, index: int, mnemonic: str, *values):
    return {"node_type":"instruction","instruction_id":uid(f"{controller}/{rung}/{index}/{mnemonic}"),"mnemonic":mnemonic,
            "operands":[operand(controller, *v) if isinstance(v,tuple) else operand(controller,v) for v in values],"metadata":{}}

def controller(name, tags, rung_specs):
    rungs=[]
    for number,(comment,specs) in enumerate(rung_specs,1):
        nodes=[ins(name,str(number),i,*spec) for i,spec in enumerate(specs)]
        rungs.append({"rung_id":uid(f"{name}/rung/{number}"),"comment":comment,"nodes":nodes,"metadata":{}})
    pid=uid(f"{name}/program"); rid=uid(f"{name}/routine")
    return {"controller_id":uid(f"controller/{name}"),"name":name,"description":"Native integrated demonstration controller",
      "compatibility_profile":"RSM-LOGIX-CORE-1","tags":tags,"programs":[{"program_id":pid,"name":"MainProgram","description":"",
      "routines":[{"routine_id":rid,"name":"MainRoutine","description":"","rungs":rungs,"metadata":{}}],"metadata":{}}],
      "cyclic_task":{"name":"MainTask","program_order":[pid]},"produced_tags":[],"consumed_tags":[],"metadata":{}}

def main():
    a="controller-a"; b="controller-b"
    at=[tag(a,"StartPB","BOOL",forceable=True),tag(a,"StopPB","BOOL"),tag(a,"ResetPB","BOOL"),tag(a,"MotorRun","BOOL",safe_value=False),
      tag(a,"MotorLatched","BOOL"),tag(a,"StartOneShot","BOOL"),tag(a,"StartDelay","TIMER",preset=100),tag(a,"StartCounter","COUNTER",preset=3),
      tag(a,"TemperaturePV","REAL",20.0,unit="degC"),tag(a,"TemperatureSP","REAL",60.0,unit="degC"),tag(a,"TemperatureError","REAL",0.0),
      tag(a,"HighTemperature","BOOL"),tag(a,"HighHighTemperature","BOOL"),tag(a,"RemotePermitProduced","BOOL"),tag(a,"MaintenanceMode","BOOL"),
      tag(a,"DemoDintA","DINT",12),tag(a,"DemoDintB","DINT",3),tag(a,"DemoDintResult","DINT",0),tag(a,"DemoRealResult","REAL",0.0)]
    ar=[("Start latch",[("XIC","StartPB"),("XIO","StopPB"),("OTL","MotorLatched")]),
      ("Stop safely unlatches",[("XIC","StopPB"),("OTU","MotorLatched")]),
      ("Motor output safe-state logic",[("XIC","MotorLatched"),("XIO","MaintenanceMode"),("OTE","MotorRun")]),
      ("One-shot start counter",[("XIC","StartPB"),("ONS",),("CTU","StartCounter")]),
      ("Start delay",[("XIC","MotorRun"),("TON","StartDelay")]),
      ("Reset timer and counter",[("XIC","ResetPB"),("RES","StartDelay"),("RES","StartCounter")]),
      ("Temperature error",[("SUB","TemperatureSP","TemperaturePV","TemperatureError")]),
      ("High comparison",[("GT","TemperaturePV",60.0),("OTE","HighTemperature")]),
      ("High-high comparison",[("GE","TemperaturePV",80.0),("OTE","HighHighTemperature")]),
      ("Produced permit",[("XIC","MotorRun"),("LE","TemperaturePV",80.0),("OTE","RemotePermitProduced")]),
      ("Comparison coverage: EQ",[("EQ","DemoDintA",12),("MOV","DemoDintA","DemoDintResult")]),
      ("Comparison coverage: NE",[("NE","DemoDintA","DemoDintB"),("ADD","DemoDintA","DemoDintB","DemoDintResult")]),
      ("Comparison coverage: LT",[("LT","DemoDintB","DemoDintA"),("SUB","DemoDintA","DemoDintB","DemoDintResult")]),
      ("Arithmetic coverage: MUL",[("MUL","DemoDintA","DemoDintB","DemoDintResult")]),
      ("Arithmetic coverage: DIV",[("DIV","DemoDintA","DemoDintB","DemoDintResult")]),
      ("Arithmetic coverage: NEG",[("NEG","DemoDintB","DemoDintResult")]),
      ("Arithmetic coverage: ABS",[("ABS","DemoDintResult","DemoDintResult")]),
      ("Arithmetic coverage: CLR",[("XIC","ResetPB"),("CLR","DemoRealResult")])]
    bt=[tag(b,"RemotePermitConsumed","BOOL"),tag(b,"RemotePermitQualityGood","BOOL"),tag(b,"RemotePermitStale","BOOL"),tag(b,"RemotePermitBad","BOOL"),
        tag(b,"RemoteLamp","BOOL",safe_value=False),tag(b,"LocalEnable","BOOL"),tag(b,"RouteHealthy","BOOL"),tag(b,"RouteFault","BOOL")]
    br=[("Fail-safe remote lamp: every value and companion quality condition is required",[("XIC","RemotePermitConsumed"),("XIC","RemotePermitQualityGood"),("XIO","RemotePermitStale"),("XIO","RemotePermitBad"),("XIC","LocalEnable"),("OTE","RemoteLamp")]),
        ("Route healthy",[("XIC","RemotePermitQualityGood"),("XIO","RemotePermitStale"),("XIO","RemotePermitBad"),("OTE","RouteHealthy")]),
        ("Route fault",[("XIO","RouteHealthy"),("OTE","RouteFault")])]
    ca=controller(a,at,ar); cb=controller(b,bt,br)
    produced=uid("produced/remote-permit"); ca["produced_tags"]=[{"produced_tag_id":produced,"source_tag_id":uid(f"{a}/tag/RemotePermitProduced"),"publish_name":"RemotePermit","update_policy":{"mode":"ON_CHANGE_WITH_HEARTBEAT","heartbeat_ms":250},"description":"Fail-safe remote permission"}]
    cb["consumed_tags"]=[{"consumed_tag_id":uid("consumed/remote-permit"),"destination_tag_id":uid(f"{b}/tag/RemotePermitConsumed"),"source_controller_id":ca["controller_id"],"source_produced_tag_id":produced,"expected_update_interval_ms":250,"timeout_ms":750,"stale_behavior":"substitute","hold_last_value":False,"substitute_value":False,"quality_handling":{"good_tag_id":uid(f"{b}/tag/RemotePermitQualityGood"),"stale_tag_id":uid(f"{b}/tag/RemotePermitStale"),"bad_tag_id":uid(f"{b}/tag/RemotePermitBad"),"safe_write_order":["value","good","bad","stale"]}}]
    project={"format":"rsmicro-project","format_version":1,"project_id":uid("project"),"name":"RSmicro Integrated Demo","description":"Two native controllers with fail-safe routing, alarms, historian, and SCADA.","controllers":[ca,cb],
      "deployments":[{"deployment_id":uid(f"deployment/{x}"),"name":f"{x} native","controller_id":uid(f"controller/{x}"),"target_platform":"native","board_identifier":None,"connection":{"host":"127.0.0.1","port":0},"devices":[],"bindings":[],"driver_configuration":{"outputs_default_safe":True},"metadata":{}} for x in (a,b)],
      "scada":{"screens":[{"screen_id":uid(f"screen/{x}"),"name":x,"path":f"screens/{x}.json"} for x in ("overview","controller_a","controller_b","alarms","trends")],
      "alarms":[],"historian":{"definitions":[]},"metadata":{}},"metadata":{"release_status":"native-software-experimentation","hardware_validated":False}}
    OUT.mkdir(parents=True,exist_ok=True); (OUT/"project.rsmproj").write_text(json.dumps(project,indent=2)+"\n")
    return 0
if __name__ == "__main__": raise SystemExit(main())
