# Current status

RSmicro Task 9A.2 provides a canonical project model, deterministic compiler, portable C99 runtime, native binding/simulator, RSM Link library, offline Studio project/routine view, and a canonical offline SCADA screen loader/renderer. The compatibility contract is RSM-LOGIX-CORE-1 profile **2.0.0**, instruction ABI **2**, image format **2.0**, and runtime ABI **1.2**.

## Ready for experimentation

- Canonical project validation and deterministic controller compilation.
- Program-image inspection, produced/consumed metadata, and deployment admission.
- Portable C core and Python native simulation on a host machine.
- Exact state diagnostics/snapshots, write traces, unload/reload, and larger-image reloads.
- Offline Studio project tree and ladder rendering.
- Canonical, project-confined SCADA screen loading and offline rendering.
- Legacy PLC ASCII editor/local simulator and preserved board tooling.

## Foundations, not complete products

- `rsm-node` opens/configures its socket and links the core/protocol foundations, but does not yet serve RSM Link requests or run a downloaded controller cyclically.
- `rsmicro-tagd` validates canonical project/controller identities and has API/supervisor scaffolding, but no proven end-to-end controller tag stream, routing, alarm, or historian lifecycle.
- Studio's compile/download/connect/mode/simulation menu actions are mostly unwired; use the CLI for validated compile/native simulation.
- SCADA renders canonical screens but does not yet consume live broker updates or issue operator writes. Offline values are visibly STALE.

## Evidence boundary

`tools/validate_repository.py` validates checked-in paths, generated registries, canonical broker/project identities, production-path screen parsing, version claims, and loopback defaults. `tools/run_integrated_demo.py` compiles each demo controller twice to separate files, compares bytes, and inspects both images. These are repository/compiler smoke checks only.

Live node + broker lifecycle, broker-mediated routing/fail-safe behavior, Studio online operation, and live standalone SCADA are **NOT_IMPLEMENTED** in this evidence.

## Platform matrix

| Platform | Status |
| --- | --- |
| Linux C runtime and Python native simulator | locally exercised host software; not hard real-time or safety certified |
| macOS | checked-in hosted workflow; do not call passing without a visible green run |
| Windows | DLL export and multi-config workflow are implemented; do not call passing without a visible green run |
| CircuitPython / MicroPython | preserved legacy targets; physical hardware **UNVERIFIED** |
| Propeller 2 / TAQOZ | preserved legacy target; physical hardware **UNVERIFIED** |

No physical I/O polarity, watchdog, power-cycle, field networking, or safety behavior is validated by this release evidence. RSmicro is experimental and not safety-certified.
