# Native controller node

`rsm-node` is a C-runtime process linking `rsmcore` and transport-independent `rsmlink`, without embedding Python. It defaults to PROGRAM mode, a 10 ms monotonic scheduling interval, and `127.0.0.1:7580`; `--help` documents bounded configuration, logging, startup image/deployment, rollback, readiness, and test-duration options.

The node layer owns sockets, deployment JSON, virtual I/O, scheduling, bounded FIFO commands, transfers, sessions, and safe shutdown; these do not belong in `rsmcore`. It is deterministic host software, not certified hard real-time or safety behavior. Previous validated images are process-lifetime rollback state only; persistent dual-slot embedded storage is future work.

The Task 9A.1 deterministic smoke does not launch a node or broker: live node/broker lifecycle and physical-node behavior are **NOT_IMPLEMENTED/out of scope for that evidence**. No physical target has been validated; all hardware status is **UNVERIFIED**.
