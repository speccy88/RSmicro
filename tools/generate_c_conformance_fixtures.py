#!/usr/bin/env python3
"""Generate language-neutral, executable semantic fixtures for the C runtime.

Fixture v2 steps model lifecycle, I/O and failure operations.  Each step may assert
multiple scalar or TIMER/COUNTER member values, status, mode, diagnostics, faults,
force state and HAL output writes.  v1's single ``expect`` is accepted only as a
compatibility shorthand and is emitted as an assertion.
"""
import argparse
import json
from pathlib import Path
from rsmicro.compiler.image import build
from rsmicro.compiler.ir import IRInstruction, IROperand, IRProgram, IRTag
from rsmicro.compiler.generated_opcodes import OPCODES, PROFILE_ID, INSTRUCTION_ABI

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "profiles/rsm-logix-core-1/conformance"
OUT = ROOT / "runtime/generated"
OPERATION = {"prescan": 1, "postscan": 2, "scan": 3, "write": 4,
             "run": 5, "program": 6, "test": 7, "force": 8,
             "clear_force": 9, "clear_all_forces": 10, "unload": 11, "load": 12,
             "read": 13}
STATUS = {"OK": 0, "INVALID_ARGUMENT": 1, "INVALID_STATE": 2,
          "BUFFER_TOO_SMALL": 3, "OUT_OF_MEMORY": 4, "BAD_IMAGE": 5,
          "BAD_CRC": 6, "UNSUPPORTED_IMAGE_VERSION": 7,
          "UNSUPPORTED_PROFILE": 8, "UNSUPPORTED_ABI": 9,
          "UNSUPPORTED_OPCODE": 10, "TYPE_MISMATCH": 11,
          "TAG_NOT_FOUND": 12, "MEMBER_NOT_FOUND": 13,
          "NOT_WRITABLE": 14, "FAULTED": 15, "HAL_ERROR": 16,
          "SCAN_OVERRUN": 17, "QUEUE_FULL": 18}
MODE = {"PROGRAM": 0, "RUN": 1, "TEST": 2, "FAULTED": 3}
MEMBER = {"PRE": 1, "ACC": 2, "EN": 3, "TT": 4, "DN": 5,
          "CU": 6, "CD": 7, "OV": 8, "UN": 9}
FAULT = {"NONE": 0, "IMAGE": 1, "CONFIGURATION": 2, "MEMORY": 3,
         "EXECUTION": 4, "NUMERIC": 5, "TIMER": 6, "COUNTER": 7,
         "HAL": 8, "WATCHDOG": 9, "INTERNAL": 10}


def operand(value):
    if isinstance(value, dict) and "tag" in value:
        return IROperand("tag", value["type"], int(value["tag"]), value.get("member"))
    if isinstance(value, bool):
        return IROperand("literal", "BOOL", value)
    if isinstance(value, int):
        return IROperand("literal", "DINT", value)
    return IROperand("literal", "REAL", float(value))


def image(fixture):
    tags = tuple(IRTag(i, f"00000000-0000-4000-8000-{i:012d}", t["name"], t["type"],
                       t.get("storage", "INTERNAL"), t.get("initial", t.get("preset", 0)), False)
                 for i, t in enumerate(fixture["tags"]))
    instructions, state = [], 0
    for i, spec in enumerate(fixture["program"]):
        mnemonic = spec["mnemonic"]
        opcode = {"BRANCH_BEGIN": 240, "BRANCH_LANE_BEGIN": 241,
                  "BRANCH_LANE_END": 242, "BRANCH_END": 243}.get(mnemonic, OPCODES.get(mnemonic))
        if opcode is None:
            raise ValueError(f"{fixture['id']}: unsupported fixture mnemonic {mnemonic}")
        slot = state if mnemonic in {"TON", "CTU", "CTD"} else None
        state += slot is not None
        instructions.append(IRInstruction(i, f"00000000-0000-4000-8001-{i:012d}", mnemonic, opcode,
            tuple(operand(v) for v in spec.get("operands", [])), slot, f"fixture/{fixture['id']}/{i}"))
    ir = IRProgram(PROFILE_ID, INSTRUCTION_ABI, "00000000-0000-4000-8000-000000000001", tags,
                   tuple(instructions), ({"id": 0, "uuid": "r", "name": "fixture"},),
                   ({"id": 0, "uuid": "rung", "routine_id": 0, "start": 0,
                     "count": len(instructions)},), 0)
    return build(ir)[0]


def cvalue(value, typ):
    if typ == "BOOL": return "{RSM_TYPE_BOOL,{.boolean=%du}}" % (1 if value else 0)
    if typ == "DINT":
        dint = int(value)
        # MSVC parses -2147483648 as unary minus applied to an unsigned literal.
        literal = "INT32_MIN" if dint == -(2**31) else str(dint)
        return "{RSM_TYPE_DINT,{.dint=%s}}" % literal
    # C requires a decimal point or exponent before a floating suffix (``99f`` is invalid).
    return "{RSM_TYPE_REAL,{.real=%.9gf}}" % float(value) if ("." in (text := format(float(value), ".9g")) or "e" in text or "E" in text) else "{RSM_TYPE_REAL,{.real=%s.0f}}" % text


def bytes_c(raw): return ",".join("0x%02x" % b for b in raw)


def assertions(step):
    values = list(step.get("assert", step.get("assertions", [])))
    if "expect" in step:
        values.append(step["expect"])
    return values


def render():
    fixtures = [json.loads(p.read_text()) for p in sorted(FIXTURES.glob("*-core.json"))]
    for f in fixtures:
        required = {"id", "instruction", "tags", "program", "steps"}
        if not required <= set(f): raise ValueError(f"{f.get('id', '<unknown>')}: missing executable semantic fields")
        times = [int(s.get("time_us", int(s.get("time_ms", 0))*1000)) for s in f["steps"]]
        if times != sorted(times) and not f.get("allow_clock_wrap", False): raise ValueError(f"{f['id']}: timestamps are not monotonic")
        for s in f["steps"]:
            for a in assertions(s):
                if not {"tag", "type", "value"} <= set(a): raise ValueError(f"{f['id']}: malformed assertion")
                if "member" in a and a["member"] not in MEMBER: raise ValueError(f"{f['id']}: unknown member")
            if s.get("status", "OK") not in STATUS: raise ValueError(f"{f['id']}: unknown status")
    h = '''/* Generated by tools/generate_c_conformance_fixtures.py; do not edit. */
#ifndef RSM_CONFORMANCE_FIXTURES_H
#define RSM_CONFORMANCE_FIXTURES_H
#include <stddef.h>
#include <stdint.h>
#include "rsmicro/rsm_types.h"
typedef struct { uint32_t tag; uint8_t member; rsm_value_t value; } rsm_conformance_assertion_t;
typedef struct { uint32_t tag; rsm_bool_t forced; rsm_value_t logical; rsm_value_t effective; } rsm_conformance_force_assertion_t;
typedef struct { uint32_t slot; uint8_t edge; uint8_t valid; uint64_t time_us; } rsm_conformance_instruction_state_assertion_t;
typedef struct { uint32_t rung; rsm_bool_t power; } rsm_conformance_rung_power_assertion_t;
typedef struct { uint32_t tag; rsm_value_t value; } rsm_conformance_write_assertion_t;
typedef struct { uint8_t operation; uint64_t time_us; uint32_t tag; rsm_value_t value; int expected_status; int expected_mode; uint64_t expected_scan_count; int expected_fault_category; uint32_t expected_fault_code; int32_t expected_output_writes; const rsm_conformance_assertion_t *assertions; size_t assertion_count; const rsm_conformance_force_assertion_t *forces; size_t force_count; const rsm_conformance_instruction_state_assertion_t *instruction_states; size_t instruction_state_count; const rsm_conformance_rung_power_assertion_t *rung_powers; size_t rung_power_count; uint8_t write_trace_declared; const rsm_conformance_write_assertion_t *writes; size_t write_count; } rsm_conformance_step_t;
typedef struct { const char *id; const char *instruction; const uint8_t *image; size_t image_size; const rsm_conformance_step_t *steps; size_t step_count; } rsm_conformance_fixture_t;
extern const rsm_conformance_fixture_t rsm_conformance_fixtures[];
extern const size_t rsm_conformance_fixture_count;
#endif
'''
    parts = ['/* Generated by tools/generate_c_conformance_fixtures.py; do not edit. */\n#include "rsm_conformance_fixtures.h"\n']
    rows = []
    for n, f in enumerate(fixtures):
        parts.append("static const uint8_t image_%d[]={%s};\n" % (n, bytes_c(image(f))))
        steps = []
        for x, s in enumerate(f["steps"]):
            aa = assertions(s)
            rendered = []
            for a in aa:
                rendered.append("{%d,%d,%s}" % (int(a["tag"]), MEMBER.get(a.get("member"), 0), cvalue(a["value"], a["type"])))
            assertion_ptr, assertion_count = "NULL", "0"
            if rendered:
                parts.append("static const rsm_conformance_assertion_t assertions_%d_%d[]={%s};\n" % (n, x, ",".join(rendered)))
                assertion_ptr = "assertions_%d_%d" % (n, x)
                assertion_count = "sizeof assertions_%d_%d/sizeof assertions_%d_%d[0]" % (n, x, n, x)
            state = s.get("state", {})
            forces = state.get("forces", [])
            instruction_states = state.get("instruction_states", [])
            rung_powers = state.get("rung_powers", [])
            writes = s.get("write_trace", [])
            def rendered_array(name, typ, values, render_value):
                if not values: return "NULL", "0"
                parts.append("static const %s %s_%d_%d[]={%s};\n" % (typ, name, n, x, ",".join(render_value(v) for v in values)))
                return "%s_%d_%d" % (name, n, x), "sizeof %s_%d_%d/sizeof %s_%d_%d[0]" % (name, n, x, name, n, x)
            force_ptr, force_count = rendered_array("forces", "rsm_conformance_force_assertion_t", forces, lambda v: "{%d,%d,%s,%s}" % (int(v["tag"]), int(bool(v["enabled"])), cvalue(v["logical"], v["type"]), cvalue(v["effective"], v["type"])))
            state_ptr, state_count = rendered_array("instruction_states", "rsm_conformance_instruction_state_assertion_t", instruction_states, lambda v: "{%d,%d,%d,UINT64_C(%d)}" % (int(v["slot"]), int(bool(v["edge"])), int(bool(v["valid"])), int(v.get("time_us", 0))))
            rung_ptr, rung_count = rendered_array("rung_powers", "rsm_conformance_rung_power_assertion_t", rung_powers, lambda v: "{%d,%d}" % (int(v["rung"]), int(bool(v["power"]))))
            write_ptr, write_count = rendered_array("writes", "rsm_conformance_write_assertion_t", writes, lambda v: "{%d,%s}" % (int(v["tag"]), cvalue(v["value"], v["type"])))
            write = s.get("write", s.get("force", s))
            fault = s.get("fault", {})
            diagnostics = s.get("diagnostics", {})
            steps.append("{%d,UINT64_C(%d),%d,%s,%d,%d,UINT64_C(%d),%d,%d,%d,%s,%s,%s,%s,%s,%s,%s,%s,%d,%s,%s}" % (
                OPERATION[s["operation"]], int(s.get("time_us", int(s.get("time_ms", 0))*1000)), int(write.get("tag", 0)),
                cvalue(write.get("value", False), write.get("type", "BOOL")), STATUS[s.get("status", "OK")],
                MODE.get(s.get("mode", ""), -1), int(diagnostics.get("scan_count", 18446744073709551615)),
                FAULT.get(fault.get("category", ""), -1), int(fault.get("code", 0)),
                int(s.get("output_writes", -1)), assertion_ptr, assertion_count,
                force_ptr, force_count, state_ptr, state_count, rung_ptr, rung_count,
                int("write_trace" in s), write_ptr, write_count))
        parts.append("static const rsm_conformance_step_t steps_%d[]={%s};\n" % (n, ",".join(steps)))
        rows.append('{"%s","%s",image_%d,sizeof image_%d,steps_%d,sizeof steps_%d/sizeof steps_%d[0]}' %
                    (f["id"], f["instruction"], n, n, n, n, n))
    parts.append("const rsm_conformance_fixture_t rsm_conformance_fixtures[]={%s};\n" % ",\n".join(rows))
    parts.append("const size_t rsm_conformance_fixture_count=sizeof rsm_conformance_fixtures/sizeof rsm_conformance_fixtures[0];\n")
    return h, "".join(parts)


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("--check", action="store_true"); args = parser.parse_args()
    rendered = render(); targets = [(OUT / "rsm_conformance_fixtures.h", rendered[0]), (OUT / "rsm_conformance_fixtures.c", rendered[1])]
    if args.check: return int(any(not p.exists() or p.read_text() != text for p, text in targets))
    OUT.mkdir(parents=True, exist_ok=True)
    for path, text in targets: path.write_text(text)
    return 0

if __name__ == "__main__": raise SystemExit(main())
