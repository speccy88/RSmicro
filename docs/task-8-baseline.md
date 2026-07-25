# Task 8 baseline

Baseline date: 2026-07-25. Starting commit: `bfb432d339557d2964cc22121e5ed97ca2a89192`. The working tree was clean.

| Item | Observed baseline |
|---|---|
| Host | Linux, Codex Cloud container |
| Python | 3.14.4 |
| CMake | 3.28.3 |
| GCC | 13.3.0 |
| Clang | 17.0.0 |
| PySide6 / Qt | Not installed; Tasks 1–6 contained no Studio/Qt package |
| Editable install | Failed because the environment package proxy returned HTTP 403 while pip attempted to obtain the build requirement |
| pytest | Failed collection: 13 modules could not import `plc_ascii`/`rsmicro` after editable installation failed |
| CTest | 4/4 passed (`rsmlink`, runtime, conformance, node queue) |
| generators | All three generators present passed `--check`; no separate RSM Link fixture generator existed |

Baseline entry points were `plc-ascii`, `plc-ascii-cli`, `plc-runtime`, `rsmicro`, and `rsmicro-tagd`. CMake built `rsmlink`, `rsmcore` static/shared, `rsmcore_demo`, `rsm-node`, and four test executables. Existing examples comprised six legacy JSON projects, deterministic migrated copies, compiler, native-core, and native-simulator examples. Preserved targets were CircuitPython, MicroPython, and Propeller 2/TAQOZ; none had physical validation evidence.

Known starting limitations: Task 7 (PySide6 Studio and standalone SCADA) was not present; there were no CI workflows, integrated demonstration, repository validator, package build tools, ruff/mypy configuration, or Task 8 release documents. The only `NotImplementedError` occurrences were abstract legacy I/O methods; SCADA CLI also caught that exception. No skipped tests were collected. Hardware remains unverified.
