# Native controller node status

`rsm-node` is currently a **node foundation**, not an implemented controller service. It links the portable `rsmcore` and transport-independent `rsmlink` libraries and provides bounded command-line configuration around a loopback listener.

Implemented today:

- C99 process linking `rsmcore` and `rsmlink` without embedding Python.
- Loopback-default listener/configuration shell.
- PROGRAM-mode and scheduling/configuration defaults.
- Strict-warning native build and bounded process tests.

Not implemented today:

- Accepting and serving RSM Link sessions.
- Decoding request frames and returning protocol responses.
- Receiving, validating, activating, or rolling back downloaded `.rsm` images.
- Running a cyclic controller scan from the node process.
- Tag manifest/read/write/force/subscription operations.
- Publishing unsolicited tag updates or fault events.
- Persistent dual-slot image storage or hardware I/O.

Those responsibilities belong in the node layer rather than `rsmcore`, but describing ownership is not evidence of implementation. The deterministic repository smoke does not launch a node/broker lifecycle.

`rsm-node --version` and documentation must agree with runtime ABI **1.2**. RSM Link remains unauthenticated and unencrypted; keep all experiments on loopback or an isolated trusted network. No physical target is validated, and all hardware status is **UNVERIFIED**.
