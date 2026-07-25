# Task 2 baseline

* Starting commit: `430744ebb70df9bb0f65b5616bb1aceb76c0c77e`.
* Working tree: clean on branch `work`.
* Baseline command: `python -m pip install -e ".[dev]"` failed because the isolated build attempted to reach the blocked package index for setuptools. Consequently `pytest -q` had nine collection errors (`plc_ascii`/`rsmicro` were not installed).
* Canonical format: `rsmicro-project`, version 1. The model has controllers, programs, routines, ordered rungs, instructions/parallel branches, UUID tag operands, literals, deployments, bindings, and produced/consumed declarations.
* Types already modeled: BOOL, DINT, REAL, TIMER, COUNTER; composite member constants existed.
* Migrated instructions observed: XIC, XIO, OTE, OTL, OTU, TON, CTU, MOV, ADD, SUB, MUL, DIV, EQ, NE, GT, LT, GTE, LTE. Aliases GTE/LTE are migration artifacts.
* Compiler assumptions: UUIDs are source identity; semantic ordering is preserved; unordered tag storage is UUID-sorted; composite status members are instruction-owned; source REAL values are finite binary32.
* Legacy differences include nominal-scan timer accumulation, Python integer/float behavior, counter clamping, incomplete lifecycle/status/force semantics, and potentially colliding structural state paths. They are intentionally not changed here.
