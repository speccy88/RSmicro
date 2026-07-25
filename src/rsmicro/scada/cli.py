from __future__ import annotations
import argparse,asyncio,json,logging,signal
from pathlib import Path
from .configuration import load_config
from .service import TagBrokerService
def parser():
 p=argparse.ArgumentParser(prog="rsmicro-tagd",description="RSmicro headless SCADA tag broker");p.add_argument("--project");p.add_argument("--config",required=True);p.add_argument("--listen");p.add_argument("--port",type=int);p.add_argument("--database");p.add_argument("--log-level",choices=("error","warning","info","debug"),default="info");p.add_argument("--json-logs",action="store_true");p.add_argument("--controller-timeout-ms",type=int);p.add_argument("--heartbeat-period-ms",type=int);p.add_argument("--history-enabled",action="store_true");p.add_argument("--history-disabled",action="store_true");p.add_argument("--alarms-enabled",action="store_true");p.add_argument("--alarms-disabled",action="store_true");p.add_argument("--routing-enabled",action="store_true");p.add_argument("--routing-disabled",action="store_true");p.add_argument("--ready-file");p.add_argument("--run-duration",type=float);p.add_argument("--allow-external",action="store_true",help="explicitly permit non-loopback API binding");p.add_argument("--version",action="version",version="rsmicro-tagd 0.1.0");return p
async def run(a):
 c=load_config(a.config,allow_external=a.allow_external)
 if a.listen:c.api["listen"]=a.listen
 if a.port:c.api["port"]=a.port
 service=await TagBrokerService(c,a.database).start();ready=Path(a.ready_file) if a.ready_file else None
 if ready:ready.write_text(json.dumps(service.info())+"\n")
 stop=asyncio.Event();loop=asyncio.get_running_loop()
 for sig in (signal.SIGINT,signal.SIGTERM):
  try:loop.add_signal_handler(sig,stop.set)
  except NotImplementedError:pass
 try:
  if a.run_duration:await asyncio.wait_for(stop.wait(),a.run_duration)
  else:await stop.wait()
 except asyncio.TimeoutError:pass
 finally:
  await service.close()
  if ready and ready.exists():ready.unlink()
 return 0
def main(argv=None):
 a=parser().parse_args(argv);logging.basicConfig(level=getattr(logging,a.log_level.upper()))
 try:return asyncio.run(run(a))
 except Exception as e:logging.error("tag broker failed: %s",e);return 1
if __name__=="__main__":raise SystemExit(main())
