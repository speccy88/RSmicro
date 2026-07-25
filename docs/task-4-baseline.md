# Task 4 baseline

* Starting commit: `93e163b68771b713cdb1864c8714d0b5daedd263` (clean working tree).
* Host: Linux x86-64; Python 3.14.4; GCC 13.3.0.
* Shared library: `build/runtime/core/librsmcore.so`.
* Runtime/image/instruction ABI: no runtime query API initially; image 1.0, instruction ABI 1, profile RSM-LOGIX-CORE-1.
* Python baseline: installation failed because the isolated build could not reach setuptools; consequently pytest had 10 import collection errors.
* C baseline: 2/2 tests passed.
* Generated registry and fixture checks passed.
* Public operations: validate/size/init/deinit/load/unload, modes, scan, scalar/member read, engineering write, forces, snapshot callback, diagnostics, last fault.
* Missing operations: runtime ABI/object-size/profile queries and stable mode/type/fault names. Task 4 adds these.
* Legacy entry points remain `plc-ascii`, `plc-ascii-cli`, and `plc-runtime`; the Tk editor uses `plc_ascii.engine`.
* Existing semantic differences are recorded in `legacy-semantic-differences.md`.
* Platform limitations: only Linux shared-library and sanitizer execution were exercised here; no hardware was validated.
