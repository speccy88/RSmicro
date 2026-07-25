# Test matrix

| Subsystem | Unit | Integration | End-to-end | Linux | macOS | Windows | Hardware |
|---|---:|---:|---:|---:|---:|---:|---:|
| Project/compiler/migration | Yes | Yes | Compiler-to-native CMake harness | Yes | Yes | Yes | N/A |
| C runtime/native binding | Yes | Yes | Native demo and Python discovery smoke | Yes | Yes | Yes (Visual Studio Release DLL) | UNVERIFIED |
| RSM Link/node | Yes | Yes | Partial | Yes | Yes | **Not supported** (POSIX-only; CMake visibly disables it) | UNVERIFIED |
| Broker/historian/alarms/routes | Yes | Static/configuration only | **NOT_IMPLEMENTED** (live broker/routes are not exercised) | Yes | Yes | Yes | N/A |
| Studio/standalone SCADA | Source exists | Static screen/configuration validation only | **UNVERIFIED** (not exercised by live smoke) | Yes | Yes | Yes | N/A |

Markers are registered in `pyproject.toml`. Hardware tests must only run after explicit target selection and must state their physical prerequisites.

Every hosted platform runs registry/fixture generation checks, CMake build plus CTest, the platform-neutral Python suite, Ruff, mypy, repository validation, package build, and the static deterministic smoke. That smoke compiles and inspects images only: it does **not** launch a broker, nodes, routes, Studio, or standalone SCADA. Sanitizers run on Linux only. The Windows job intentionally uses the Visual Studio Release layout and exports `RSMICRO_CORE_LIBRARY`; native tests exercise discovery rather than hard-coding a Unix library name.
