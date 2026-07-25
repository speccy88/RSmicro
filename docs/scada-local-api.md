# Local SCADA WebSocket API

The default endpoint is `ws://127.0.0.1:7590`, JSON protocol `rsmicro-scada-json/1`. Request objects carry `type`, `request_id`, and a VIEWER, OPERATOR or ENGINEERING policy role. It exposes service/controllers/manifests, reads/writes/forces, history, alarms, routes and diagnostics. Messages, clients and queues are bounded. This UI protocol is separate from binary RSM Link.
