#!/usr/bin/env python3
import argparse,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]; BASE=ROOT/'profiles/rsm-logix-core-1'
def outputs():
 p=json.loads((BASE/'profile.yaml').read_text()); specs=[json.loads(x.read_text()) for x in sorted((BASE/'instructions').glob('*.yaml'))]
 if len({x['mnemonic'] for x in specs})!=len(specs) or len({x['opcode'] for x in specs})!=len(specs): raise ValueError('duplicate mnemonic or opcode')
 rows=sorted(specs,key=lambda x:x['opcode']); meta={x['mnemonic']:{'opcode':x['opcode'],'operands':x['operands'],'state':x['state']} for x in rows}
 py='# Generated; do not edit.\nPROFILE_ID = '+repr(p['profile_id'])+'\nPROFILE_VERSION = '+repr(p['profile_version'])+'\nINSTRUCTION_ABI = '+repr(p['instruction_abi'])+'\nOPCODES = '+repr({x['mnemonic']:x['opcode'] for x in rows})+'\nALIASES = '+repr(p['aliases'])+'\n'
 pym='# Generated; do not edit.\nINSTRUCTIONS = '+repr(meta)+'\n'
 h='/* Generated; do not edit. */\n#ifndef RSM_OPCODES_H\n#define RSM_OPCODES_H\n#define RSM_PROFILE_ID "RSM-LOGIX-CORE-1"\n#define RSM_INSTRUCTION_ABI '+str(p['instruction_abi'])+'\n#define RSM_OP_BRANCH_BEGIN 240u\n#define RSM_OP_BRANCH_LANE_BEGIN 241u\n#define RSM_OP_BRANCH_LANE_END 242u\n#define RSM_OP_BRANCH_END 243u\n'+''.join(f'#define RSM_OP_{x["mnemonic"]} {x["opcode"]}u\n' for x in rows)+'#endif\n'
 table=json.dumps({'profile_id':p['profile_id'],'profile_version':p['profile_version'],'instruction_abi':p['instruction_abi'],'instructions':rows},indent=2,sort_keys=True)+'\n'
 md='# RSM-LOGIX-CORE-1 instructions\n\n|Mnemonic|Opcode|Category|\n|---|---:|---|\n'+''.join(f'|{x["mnemonic"]}|{x["opcode"]}|{x["category"]}|\n' for x in rows)
 return {ROOT/'src/rsmicro/compiler/generated_opcodes.py':py,ROOT/'src/rsmicro/compiler/generated_instructions.py':pym,ROOT/'runtime/generated/rsm_opcodes.h':h,ROOT/'runtime/core/include/rsmicro/rsm_opcodes.h':h,BASE/'generated/instruction-table.json':table,ROOT/'docs/generated/rsm-logix-core-1-instructions.md':md}
def main():
 a=argparse.ArgumentParser(); a.add_argument('--check',action='store_true'); ns=a.parse_args(); bad=[]
 for path,data in outputs().items():
  if ns.check:
   if not path.exists() or path.read_text()!=data: bad.append(str(path.relative_to(ROOT)))
  else: path.parent.mkdir(parents=True,exist_ok=True); path.write_text(data)
 if bad: print('stale generated files: '+', '.join(bad),file=sys.stderr); return 1
 return 0
if __name__=='__main__': raise SystemExit(main())
