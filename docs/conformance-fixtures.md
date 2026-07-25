# Conformance fixtures

`profiles/rsm-logix-core-1/conformance/*-core.json` is the language-neutral input to `tools/generate_c_conformance_fixtures.py`.  The generated C data is executed by `rsmcore_conformance_tests`; it is not a catalogue or an opcode-count test.

## Fixture schema v2

A fixture contains immutable tag declarations, a target-neutral instruction stream, and ordered time-monotonic `steps`. A step declares an operation (`prescan`, `postscan`, `run`, `program`, `test`, `scan`, `write`, `force`, `clear_force`, `clear_all_forces`, or `unload`) and has one or more `assert` values. Each assertion has `tag`, `type`, `value`, and optionally a composite `member` (`PRE`, `ACC`, `EN`, `TT`, `DN`, `CU`, `CD`, `OV`, `UN`). Steps may additionally assert `status`, `mode`, `diagnostics.scan_count`, `fault.category`/`fault.code`, and cumulative `output_writes`.

`expect` remains a compatibility spelling for exactly one scalar assertion, but new cases use `assert` so unchanged destinations and independent values are checked together. A fixture must exercise real image load and C lifecycle calls. Snapshot callbacks are run after every operation and must not change scan count.

A step may also provide `state.forces` (`tag`, `enabled`, `type`, `logical`, `effective`), `state.instruction_states` (`slot`, `edge`, `valid`, `time_us`), and `state.rung_powers` (`rung`, `power`). `write_trace`, when present (including an explicit empty array), declares the exact ordered successful backing writes for that operation. The runner clears and reads the bounded public runtime trace around each operation; it does not inspect private runtime memory.

## Required matrices

The branch cases cover pre/post series logic, two and three parallel lanes, A/B/neither inputs, a false precondition, nested lanes, and branch output placement. Stateful cases cover explicit pre/postscan, mode transitions, force/clear-force, scalar and member observations, and failed operations/statuses. The canonical compiler E2E separately compiles a Project, writes an `.rsm`, and loads/scans it through a freshly built C `rsmcore` library.

Generation is deterministic:

```sh
python tools/generate_c_conformance_fixtures.py
python tools/generate_c_conformance_fixtures.py --check
```
