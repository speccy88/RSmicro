# Native controller node

`rsm-node` is the first autonomous C-runtime process. It links `rsmcore` and the transport-independent `rsmlink` library without embedding Python. It defaults to PROGRAM mode, a 10 ms monotonic scheduling interval, and `127.0.0.1:7580`. `--help` lists bounded configuration, logging, startup image/deployment, rollback, readiness, and test-duration options.

The node layer owns sockets, deployment JSON, virtual I/O, scheduling, bounded FIFO commands, transfers, sessions, and safe shutdown; none belongs in `rsmcore`. Mutating commands are copied into a fixed queue and applied FIFO at scan boundaries. Production scheduling uses monotonic deadline targets and must track missed deadlines without overlapping scans. PROGRAM and FAULTED retain network/heartbeat service without normal scans. This POSIX scheduling is useful deterministic simulation, not certified hard real-time or safety behavior.

SIGINT/SIGTERM stop acceptance and scanning, postscan when required, apply safe outputs, abort staging, close sessions/sockets, and deinitialize. Previous validated images are process-lifetime rollback state only; persistent dual-slot embedded storage is future work. No physical target uses RSM Link yet.
