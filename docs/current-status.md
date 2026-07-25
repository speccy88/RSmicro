# Current status

RSmicro 9A.1 provides a canonical project model, deterministic compiler, portable C99 runtime, native binding/simulator, RSM Link library, and a native node implementation. The supported compatibility contract is RSM-LOGIX-CORE-1 profile **2.0.0**, instruction ABI **2**, image format **2.0**, and runtime ABI **1.2**.

## Evidence boundary

`tools/validate_repository.py` validates checked-in paths, generated registries, project/config/screen parsing, version claims, and loopback defaults. `tools/run_integrated_demo.py` compiles each demo controller twice to separate files, compares bytes, and inspects both images. These are static/compiler smoke checks only.

Live node + broker lifecycle, broker-mediated routing/fail-safe behavior, Studio, and standalone SCADA are **NOT_IMPLEMENTED in the smoke evidence**. They must not be represented as passed merely because the deterministic compiler smoke passes.

## Platform matrix

| Platform | Status |
| --- | --- |
| Linux native C runtime/node and Python native simulator | host-software tested by local gates; not hard real-time or safety certified |
| CircuitPython | preserved legacy target; physical hardware **UNVERIFIED** |
| MicroPython | preserved legacy target; physical hardware **UNVERIFIED** |
| Propeller 2 / TAQOZ | preserved legacy target; physical hardware **UNVERIFIED** |

No physical I/O polarity, watchdog, power-cycle, field networking, or safety behavior is validated by this release evidence. RSmicro is experimental and not safety-certified.
