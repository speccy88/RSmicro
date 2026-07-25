# Runtime scan

RUN/TEST capture monotonic time, capture every input once, apply force overlays on reads, execute validated rungs/instructions in image order, expose final forced values to the output image, write outputs only in RUN, update integer diagnostics, then kick the watchdog. TEST suppresses physical writes. A major fault stops execution, enters FAULTED, and prevents further scans. PROGRAM-to-active performs explicit prescan; leaving active execution clears timing/edge baselines. Snapshots perform none of these operations.
