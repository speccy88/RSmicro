# Portable runtime core

`rsmcore` is the canonical, multiple-instance C99 instruction engine. It owns no OS resources and performs no allocation, I/O, sleep, logging, JSON parsing, or locking. The Python compiler remains the image producer; legacy Python and board engines remain available but are not silently redirected. Public operations cover image validation/loading, caller-arena lifecycle, PROGRAM/RUN/TEST/FAULTED modes, scanning, typed access, forces, snapshots, diagnostics, and structured faults. Physical safety certification and hardware validation are not claimed.
