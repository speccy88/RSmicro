# Deterministic compiler

The pipeline loads the canonical v1 project, performs schema and profile semantic validation, resolves UUID operands into typed local IDs, lowers branches and instructions into target-neutral IR, encodes explicit little-endian bytecode, then constructs the sectioned image, deterministic manifest, and debug map. Python is tooling, not the future canonical execution engine.

`rsmicro compile project.rsmproj --controller controller-a --output controller.rsm` writes atomically. `--warnings-as-errors`, deployment selection, JSON diagnostics, and debug stripping are supported. The programmatic `compile_project` API performs no I/O and returns diagnostics, IR, bytes, hashes, maps, and memory estimates.

Stable UUID ordering is used for unordered tags while program/routine/rung/instruction semantic order is retained. No clocks, random data, host paths, or hash iteration enter output. Limits and advanced deployment capabilities remain an area for Task 3 integration.
