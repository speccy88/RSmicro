# ADR 0011: Python native binding strategy

Accepted. Use standard-library `ctypes` against the versioned public C ABI. The library object, opaque runtime-sized buffer, arena, immutable image, HAL structures, and callbacks are retained for the runtime lifetime. Explicit `close()`/context management is primary. Status conversion is centralized. Discovery and ABI checks precede use; no private C implementation layout is represented in Python.
