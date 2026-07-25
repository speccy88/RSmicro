# Portable runtime core

`rsmcore` is the canonical, multiple-instance C99 instruction engine. It owns no OS resources and performs no allocation, I/O, sleep, logging, JSON parsing, or locking. The Python compiler remains the image producer; legacy Python and board engines remain available but are not silently redirected. Public operations cover image validation/loading, caller-arena lifecycle, PROGRAM/RUN/TEST/FAULTED modes, scanning, typed access, forces, snapshots, diagnostics, and structured faults. Physical safety certification and hardware validation are not claimed.

## Native Python integration

`NativeRuntime` serializes **every public interaction** with its per-instance re-entrant lock, including loading, lifecycle changes, mode access, scan phases, tag/force operations, diagnostics, traces, and snapshots. This makes direct calls safe to interleave with a `NativeSimulator` scan worker; the C core itself deliberately provides no locking.

The binding exposes `prescan()`, `scan()`, and `postscan()` as the C lifecycle phases. `clear_write_trace()` and `get_write_trace()` expose the bounded 64-entry write trace as immutable `WriteTrace` records. Trace entries record successful scalar logical backing writes in order; a force overlay does not alter the recorded logical value.

`snapshot()` is observational and does not scan or mutate program state. A single native traversal supplies scalar logical/effective/forced values, TIMER/COUNTER members, instruction-state slots, rung powers, mode, diagnostics, and the last fault. Snapshot callback state is retained for the entire native call.

`unload()` is only accepted by the native core in PROGRAM mode. It clears the Python image, manifest, debug map, and hash as well as the C program. Native calls that require a loaded program then report `INVALID_STATE`; `load_image()` can load a new image after a successful unload. `close()` deinitializes once, releases Python-owned arena/image metadata, and all subsequent runtime operations raise a closed-runtime error.
