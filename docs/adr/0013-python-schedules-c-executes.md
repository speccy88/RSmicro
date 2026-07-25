# ADR 0013: Python schedules, C executes

Accepted. Python owns virtual I/O, monotonic scheduling, subscriptions, and lifecycle. Every ladder scan is delegated to `rsm_runtime_scan`; Python contains no instruction interpreter. Python periodic scheduling is functional simulation, not hard real time or a safety controller.
