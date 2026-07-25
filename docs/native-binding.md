# Python native binding

`rsmicro.native` is a typed `ctypes` binding. Discovery order is explicit path, `RSMICRO_CORE_LIBRARY`, development build, package-local library, and OS lookup. Runtime ABI major 1, instruction ABI 1, image major 1, and RSM-LOGIX-CORE-1 are required. `NativeRuntime` retains the C object buffer, arena, image and HAL callbacks and supports context management, modes, scans, typed reads/writes, forces, immutable snapshots, diagnostics and faults. REAL writes are explicitly rounded to binary32. UUID and unique-name access require compiler metadata with a matching SHA-256.

Build with `rsmicro native build`; no import triggers a build. Installed wheels do not currently bundle platform libraries. No internal C pointer is exposed and no hardware support is claimed.
