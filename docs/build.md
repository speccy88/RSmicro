
## Native Python simulator

```sh
python -m pip install -e ".[dev]"
cmake -S . -B build -DRSM_BUILD_TESTS=ON -DRSM_BUILD_SHARED=ON
cmake --build build
rsmicro native info
rsmicro run-native examples/native_simulator_demo/project.rsmproj --controller controller-a --scenario examples/native_simulator_demo/scenario.json --format json
```

For an off-repository install, build once and export `RSMICRO_CORE_LIBRARY=/absolute/path/to/librsmcore.so`. No compiler/toolchain download occurs.
