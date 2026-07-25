# Porting rsmcore

A port supplies a monotonic microsecond clock and an arena. It may supply nonblocking typed endpoint read/write, watchdog, and event callbacks. Scheduling, persistence, deployment parsing, active-low adaptation, and board safe-output circuitry remain outside the core. No physical port or hardware validation is delivered by Task 3.
