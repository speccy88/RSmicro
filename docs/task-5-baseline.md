# Task 5 baseline

* Starting commit: `52c4a76bd9d3d1c8aeb3a7258287b684f15559bc` (clean working tree).
* Environment: Python 3.14.4; GCC 13.3.0.
* Python baseline: editable installation could not obtain the `setuptools>=68` build dependency because the environment's package proxy returned HTTP 403. Consequently direct `pytest -q` failed collection with 11 package-import errors.
* C baseline: strict shared build succeeded; CTest passed 2/2 tests.
* Runtime ABI: 1.0; instruction ABI: 1; image format: 1.0; profile RSM-LOGIX-CORE-1.
* Command staging: Task 4 exposes synchronous native binding operations but no network command queue.
* Virtual I/O: the native test HAL provides typed values, counters, timestamps, failures, and safe output behavior.
* Binding operations: image load, mode transitions, scans, typed read/write, force/unforce, snapshots, diagnostics, and faults.
* Link operations needed: negotiation, transfers, queued mutation, manifests, reads, subscriptions, snapshots, diagnostics, and heartbeat.
* Existing executables: `rsmcore_demo`; existing C targets: `rsmcore`, `rsmcore_shared`, and core tests.
* Preserved runtimes: legacy Python, CircuitPython, MicroPython, Propeller 2/TAQOZ, Tkinter IDE, and Task 4 native simulator.

Commands recorded: `git status`, `git rev-parse HEAD`, `python --version`, `cc --version`, editable install, `pytest -q`, strict CMake configure/build, and CTest.
