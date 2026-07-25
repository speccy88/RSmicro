from __future__ import annotations
import asyncio, json, sqlite3
from pathlib import Path
from typing import Any
from .historian_schema import *
from .errors import HistorianError
class Historian:
 def __init__(self,path,queue_size=4096,batch_size=128): self.path=Path(path); self.queue: asyncio.Queue[Any] = asyncio.Queue(queue_size); self.batch_size=batch_size; self.high_water=0; self.dropped=0; self.write_count=0; self.errors=0; self._conn: sqlite3.Connection | None=None; self._task=None
 def open(self):
  self.path.parent.mkdir(parents=True,exist_ok=True); self._conn=sqlite3.connect(self.path); self._conn.execute("PRAGMA journal_mode=WAL"); self._conn.execute("PRAGMA foreign_keys=ON"); self._conn.execute("PRAGMA busy_timeout=5000")
  version=self._conn.execute("PRAGMA user_version").fetchone()[0]
  if version>SCHEMA_VERSION: raise HistorianError(f"unsupported historian schema {version}")
  if version<1:
   with self._conn: self._conn.executescript(MIGRATION_1); self._conn.execute("INSERT OR IGNORE INTO schema_migrations VALUES(1,datetime('now'))"); self._conn.execute("PRAGMA user_version=1")
  return self
 async def start(self): self.open(); self._task=asyncio.create_task(self._writer()); return self
 def enqueue(self,tag,important=False):
  item=tag.to_dict() if hasattr(tag,"to_dict") else tag
  try: self.queue.put_nowait((item,important)); self.high_water=max(self.high_water,self.queue.qsize()); return True
  except asyncio.QueueFull: self.dropped+=1; return False
 async def _writer(self):
  while True:
   first=await self.queue.get()
   if first is None: self.queue.task_done(); break
   batch=[first]
   while len(batch)<self.batch_size:
    try:
     x=self.queue.get_nowait()
     if x is None: self.queue.task_done(); break
     batch.append(x)
    except asyncio.QueueEmpty: break
   try:
    rows=[]
    for t,_ in batch:
     v=t.get("effective_value"); typ=t.get("data_type","TEXT"); q=t["quality"]
     rows.append((t["tag_id"],t["controller_id"],t.get("program_hash"),typ,int(v) if typ=="BOOL" and v is not None else None,int(v) if typ in ("DINT","INT") and v is not None else None,float(v) if typ=="REAL" and v is not None else None,None if typ in ("BOOL","DINT","INT","REAL") else json.dumps(v),q["level"],q["reason"],int(t.get("forced",False)),t.get("source_timestamp"),t.get("receive_timestamp") or q["timestamp"],t.get("broker_sequence"),t.get("scan_number")))
    if self._conn is None: raise HistorianError("historian is not open")
    with self._conn: self._conn.executemany("INSERT INTO samples(tag_uuid,controller_uuid,program_hash,data_type,bool_value,dint_value,real_value,text_value,quality,quality_reason,forced,source_timestamp,receive_timestamp,broker_sequence,scan_number) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
    self.write_count+=len(rows)
   except Exception: self.errors+=1
   finally:
    for _ in batch: self.queue.task_done()
 def query(self,tag_uuid,start,end,maximum=10000,quality=None):
  if not start or not end or maximum<1 or maximum>10000: raise HistorianError("bounded start/end and maximum <= 10000 required")
  sql="SELECT receive_timestamp,source_timestamp,data_type,bool_value,dint_value,real_value,text_value,quality,quality_reason,forced FROM samples WHERE tag_uuid=? AND receive_timestamp BETWEEN ? AND ?"; args=[tag_uuid,start,end]
  if quality: sql+=" AND quality=?"; args.append(quality)
  if self._conn is None: raise HistorianError("historian is not open")
  rows=self._conn.execute(sql+" ORDER BY receive_timestamp LIMIT ?",(*args,maximum)).fetchall()
  return [{"receive_timestamp":r[0],"source_timestamp":r[1],"value":r[3] if r[2]=="BOOL" else r[4] if r[2] in ("DINT","INT") else r[5] if r[2]=="REAL" else json.loads(r[6]),"quality":r[7],"quality_reason":r[8],"forced":bool(r[9])} for r in rows]
 def prune(self,before):
  if self._conn is None: raise HistorianError("historian is not open")
  with self._conn: return self._conn.execute("DELETE FROM samples WHERE receive_timestamp < ?",(before,)).rowcount
 async def close(self):
  if self._task: await self.queue.join(); await self.queue.put(None); await self._task
  if self._conn: self._conn.close(); self._conn=None
