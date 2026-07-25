# Native simulation

The pipeline is canonical project → Python compiler → `.rsm` image → ctypes → `librsmcore` → C scan engine. `NativeSimulator.from_project()` compiles in memory and loads the image without interpreting logic in Python.

Manual mode uses `set_time_us`/`advance_time_us`; real mode reads `time.monotonic_ns()`. Periodic scans use one thread, a stop event, fixed deadlines and serialized native calls. This is diagnostic functional timing, not hard real-time control. Virtual inputs live in HAL endpoint storage and are captured by C on the next scan; outputs are captured only through C HAL writes (TEST suppresses writes). PROGRAM/RUN/TEST, force, snapshot, diagnostics and retained fault inspection are available. Native faults stop the worker.

Use `rsmicro native info`, `rsmicro native build`, or `rsmicro run-native PROJECT --controller ID --scenario scenario.json --format json`.
