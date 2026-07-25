# Refactor baseline

* **Starting commit:** `fab5bc339fa6c50533e0c231374e82df6efdb8e2`
* **Working tree:** clean branch `work` (`git status --short --branch` reported only `## work`).
* **Environment:** Python 3.14.4 on Linux 6.12.13 x86_64 (Codex Cloud container).
* **Install command:** `python -m pip install -e ".[dev]"`. At baseline the `dev` extra did not exist and build isolation could not reach the package index (HTTP tunnel 403), so installation failed before installing the editable package.
* **Test command/result:** `pytest -q`; collection failed with eight `ModuleNotFoundError: plc_ascii` errors because the failed editable install left `src/` off `sys.path`. This failure was recorded before changes.

## Existing architecture

Packages were `plc_ascii` (model, Tkinter IDE, simulator/engine, protocol, renderer, remote sessions, serial/subprocess transports, CircuitPython/MicroPython/Propeller 2 integration) and `plc_runtime` (native Python runtime plus CircuitPython, MicroPython, and Propeller 2/TAQOZ runtimes). Entry points were `plc-ascii`, `plc-ascii-cli`, and `plc-runtime`.

The v1 JSON project contains `name`, `runtime_target`, `rungs`, `variables`, and `bindings`. Rungs use ordered `step`/`branch` elements (older files use conditions/actions). Instructions are XIC, XIO, CMP/EQ/GT/GTE/LT/LE/NE, OTE/OTL/OTU, TON, CTU/CTD, MOV/CLR, ADD/SUB/MUL/DIV/ABS/NEG. Types are `bool`, `int`, `float`, `timer`, `counter`. The protocol is newline-delimited JSON version 1. Simulation performs cyclic rung scans, maintains scalar/timer/counter and forced state, and applies memory/GPIO bindings.

CircuitPython and MicroPython each have portable and board runtime modules; Propeller 2 has Python transport/runtime plus the preserved TAQOZ `runtime.fth`. Instruction semantics are duplicated across the desktop engine, native runtime, portable board runtimes, and TAQOZ implementation.

## Risks and preservation boundary

Names serve as legacy identity; hardware details are mixed into logical files; runtime normalization silently defaults unknown targets; inferred declarations and timer presets can create semantic ambiguity; several runtimes duplicate instruction behavior; and hardware polarity/safe-state information is incomplete. Preserve `src/plc_ascii/**`, `src/plc_runtime/**`, every original `examples/*.json`, existing tests, protocol compatibility, PDFs, and target documentation until later compiler/runtime work provides verified replacements. No physical hardware validation was performed for this refactor.
