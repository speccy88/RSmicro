# Python native binding

`rsmicro.native` is a typed `ctypes` binding. Discovery order is explicit path, `RSMICRO_CORE_LIBRARY`, development build, package-local library, and OS lookup. It requires `RSM-LOGIX-CORE-1`, runtime ABI **1.2**, instruction ABI **2**, and image format **2.0**. The binding queries these values from the loaded library and raises `NativeAbiMismatchError` rather than attempting to load an older ABI-1 / format-1 runtime or reinterpret its images.

`NativeRuntime` retains the C object buffer, arena, image, and HAL callbacks. It supports context management, mode changes, scans, typed tag reads/writes, force overlays, immutable scalar/composite snapshots, diagnostics, faults, and bounded backing-write traces. REAL writes are explicitly rounded to binary32. UUID and unique-name access require matching compiler metadata with its SHA-256.

ABI 2 images use binary `RUNTIME_RUNGS` metadata and explicit branch control records (`BRANCH_BEGIN`, `BRANCH_LANE_BEGIN`, `BRANCH_LANE_END`, `BRANCH_END`); validation occurs in the native runtime without JSON parsing. It also validates routine/rung boundaries and rejects malformed images before replacing a live program. `ONS` has one explicit writable BOOL storage operand. For source-model compatibility, compilation turns a legacy zero-operand ONS node into a deterministic hidden internal `__rsm_ons_storage_*` tag; old zero-operand ONS bytecode itself is not accepted.

Build with `rsmicro native build`; no import triggers a build. Installed wheels do not currently bundle platform libraries. No internal C pointer is exposed and no hardware support is claimed.
