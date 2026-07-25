#!/usr/bin/env python3
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; SOURCE=ROOT/"protocol/schema/protocol.json"
def render(prefix,items):
 return "/* Generated from protocol/schema/protocol.json; do not edit. */\n#ifndef "+prefix+"_H\n#define "+prefix+"_H\n"+"".join(f"#define {prefix}_{k} {v}u\n" for k,v in items.items())+"#endif\n"
def main():
 p=argparse.ArgumentParser();p.add_argument("--check",action="store_true");a=p.parse_args(); data=json.loads(SOURCE.read_text()); outputs={ROOT/"protocol/generated/rsm_link_message_ids.h":render("RSM_LINK_MESSAGE",data["messages"]),ROOT/"protocol/generated/rsm_link_error_ids.h":render("RSM_LINK_ERROR",data["errors"]),ROOT/"protocol/generated/message-table.json":json.dumps(data["messages"],indent=2,sort_keys=True)+"\n"}
 bad=[]
 for path,text in outputs.items():
  if a.check:
   if not path.exists() or path.read_text()!=text: bad.append(str(path))
  else: path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
 if bad: raise SystemExit("out of date: "+", ".join(bad))
if __name__=="__main__":main()
