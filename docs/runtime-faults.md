# Runtime faults

Faults identify category, code, scan/time, instruction/opcode/tag location, stable message ID, and major status. Image errors are ordinary load errors and never replace a loaded program. Execution, numeric, timer/counter, HAL, watchdog, and invariant failures are major: remaining logic stops and mode becomes FAULTED. Recovery is explicit through PROGRAM and reload/mode selection; forces never authorize recovery.
