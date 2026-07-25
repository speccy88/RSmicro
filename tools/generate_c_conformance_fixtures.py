#!/usr/bin/env python3
"""Generate the deterministic C fixture catalogue (fixture semantics remain JSON-owned)."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'runtime/generated'
def render():
 files=sorted((ROOT/'profiles/rsm-logix-core-1/conformance').glob('*.json'))
 rows=[(json.loads(p.read_text())['instruction'],p.name) for p in files]
 h='#ifndef RSM_CONFORMANCE_FIXTURES_H\n#define RSM_CONFORMANCE_FIXTURES_H\n#include <stddef.h>\ntypedef struct {const char *instruction; const char *source;} rsm_conformance_fixture_t;\nextern const rsm_conformance_fixture_t rsm_conformance_fixtures[];\nextern const size_t rsm_conformance_fixture_count;\n#endif\n'
 c='#include "rsm_conformance_fixtures.h"\nconst rsm_conformance_fixture_t rsm_conformance_fixtures[]={\n'+''.join(f' {{"{a}","{b}"}},\n' for a,b in rows)+'};\nconst size_t rsm_conformance_fixture_count=sizeof rsm_conformance_fixtures/sizeof rsm_conformance_fixtures[0];\n'
 return h,c
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--check',action='store_true');a=ap.parse_args();h,c=render();targets=[(OUT/'rsm_conformance_fixtures.h',h),(OUT/'rsm_conformance_fixtures.c',c)]
 if a.check: return 1 if any(not p.exists() or p.read_text()!=s for p,s in targets) else 0
 OUT.mkdir(parents=True,exist_ok=True)
 for p,s in targets:p.write_text(s)
 return 0
if __name__=='__main__':raise SystemExit(main())
