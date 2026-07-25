
## Native Python simulator

```sh
python -m pip install -e ".[dev]"
cmake -S . -B build -DRSM_BUILD_TESTS=ON -DRSM_BUILD_SHARED=ON
cmake --build build
rsmicro native info
rsmicro run-native examples/native_simulator_demo/project.rsmproj --controller controller-a --scenario examples/native_simulator_demo/scenario.json --format json
```

For an off-repository install, build once and set `RSMICRO_CORE_LIBRARY` to the built shared library: `librsmcore.so` on Linux, `librsmcore.dylib` on macOS, or `rsmcore.dll` on Windows (normally `build/runtime/core/Release/rsmcore.dll` with Visual Studio). No compiler/toolchain download occurs.

`RSM_BUILD_NODE` defaults to `ON` on POSIX hosts. The current socket-based `rsm-node` is POSIX-only, so CMake visibly disables that target on Windows; the portable core, protocol library, CTest suite, and Python/native discovery checks remain supported there.
