# ADR 0015: Native simulator concurrency

Accepted. A runtime permits one operation at a time. `NativeSimulator` serializes scans and mutations with one lock, uses one stoppable worker and fixed monotonic deadlines, and dispatches immutable events outside the native call. Separate runtime instances are independent.
