# Task 7 baseline

* Starting commit: `bfb432d339557d2964cc22121e5ed97ca2a89192` (clean working tree).
* Host: Linux 6.12.13 x86_64; Python 3.14.4.
* PySide6: not installed in the baseline environment.
* Editable installation: blocked because the package index returned HTTP 403 while obtaining the isolated `setuptools>=68` build dependency.
* Python baseline: collection failed (13 import errors) because that editable installation did not complete.
* C baseline: configure/build passed; CTest passed 4/4 tests.
* GUI entry points: `plc-ascii` (Tkinter IDE), `plc-ascii-cli`, and `plc-runtime`. These remain preserved.

The canonical v1 project dataclasses provide deterministic load/atomic save, validation and legacy migration. The compiler provides structured diagnostics, manifests/debug maps and RSM-LOGIX-CORE-1 images. `NativeRuntime`/`NativeSimulator` provide C-runtime loading, scans, deterministic time, HAL values, forces and snapshots. RSM Link provides connection, capability, transfer, mode, tag, subscription, force and diagnostic operations. The loopback tag broker API provides manifests, reads/writes, quality, alarm acknowledgement, historian queries and routes. Existing `Scada` screens were untyped dictionaries: stable versioned safe screen/object models and graphical rendering were the principal schema gap.

Legacy Tkinter, CircuitPython, MicroPython, Propeller 2, native runtime, node, protocol and SCADA service sources must remain intact.
