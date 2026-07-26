# RSmicro beginner tutorial

This tutorial exercises the parts of RSmicro that work today: canonical validation, deterministic compilation, image inspection, the native C core, Studio's offline project view, and SCADA's offline screen preview.

## 1. Install prerequisites

You need Python 3.11 or newer, CMake 3.20 or newer, and a C99 compiler.

### Ubuntu/Debian

```bash
sudo apt update
sudo apt install -y python3 python3-venv build-essential cmake
```

### macOS

Install Xcode Command Line Tools and CMake:

```bash
xcode-select --install
brew install cmake python@3.11
```

### Windows

Install Python 3.11+, CMake, and Visual Studio 2022 Build Tools with the **Desktop development with C++** workload. Run the following commands in PowerShell.

## 2. Clone and create an environment

### Linux and macOS

```bash
git clone https://github.com/speccy88/RSmicro.git
cd RSmicro
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e .
```

### Windows PowerShell

```powershell
git clone https://github.com/speccy88/RSmicro.git
Set-Location RSmicro
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

Check the tools:

```bash
rsmicro --help
rsmicro-studio --version
rsmicro-scada --version
```

## 3. Build and discover the native C core

Use the default `build/` directory so native discovery works without environment variables:

```bash
rsmicro native build --clean --release
rsmicro native info --format json
```

`native info` should report runtime ABI 1.2, instruction ABI 2, image format 2.0, and profile `RSM-LOGIX-CORE-1`.

If you deliberately use a custom build directory, point Python at the exact shared library:

```bash
export RSMICRO_CORE_LIBRARY=/absolute/path/to/librsmcore.so   # Linux
export RSMICRO_CORE_LIBRARY=/absolute/path/to/librsmcore.dylib # macOS
```

PowerShell example:

```powershell
$env:RSMICRO_CORE_LIBRARY = "C:\absolute\path\to\rsmcore.dll"
$env:RSMICRO_CMAKE_CONFIG = "Release"
```

## 4. Validate a canonical project

```bash
rsmicro validate examples/integrated_demo/project.rsmproj
rsmicro show-project examples/integrated_demo/project.rsmproj
```

Validation is compiler-owned. Invalid UUIDs, duplicate identities or tag names, malformed branch structures, bad scalar values, incompatible profiles, and invalid deployment bindings are rejected with structured diagnostics before lowering or image generation.

## 5. Compile a controller

```bash
mkdir -p build/demo
rsmicro compile examples/integrated_demo/project.rsmproj \
  --controller controller-a \
  --output build/demo/controller-a.rsm \
  --manifest build/demo/controller-a.manifest.json \
  --debug-map build/demo/controller-a.debug.json
```

The controller can be selected by canonical UUID or its unique display name. A failed compile does not emit a usable program image.

Compile it a second time and compare the bytes:

```bash
rsmicro compile examples/integrated_demo/project.rsmproj \
  --controller controller-a --output build/demo/controller-a-second.rsm
cmp build/demo/controller-a.rsm build/demo/controller-a-second.rsm
```

No output from `cmp` means the images are byte-identical.

## 6. Inspect the program image

```bash
rsmicro inspect-image build/demo/controller-a.rsm --format json
```

The report includes image/profile versions, controller identity, deterministic sections, tag/rung counts, produced/consumed metadata, and checksums.

## 7. Run the real C core locally

```bash
rsmicro run-native examples/integrated_demo/project.rsmproj \
  --controller controller-a \
  --mode run \
  --duration 0.25 \
  --show-tags \
  --show-diagnostics \
  --format json
```

This compiles the selected controller, loads the resulting image into `rsmcore`, enters RUN, executes bounded scans, and returns tags and diagnostics. It does not use `rsm-node` or a network broker.

For manual stepping and interactive tag commands:

```bash
rsmicro run-native examples/integrated_demo/project.rsmproj \
  --controller controller-a --manual --interactive --show-tags
```

Use `Ctrl-D` on Linux/macOS or `Ctrl-Z`, Enter on Windows to leave interactive input.

## 8. Open Studio

```bash
rsmicro-studio examples/integrated_demo/project.rsmproj
```

Studio currently provides an offline project tree and ladder-routine rendering. Controller-qualified tabs keep same-named routines distinct. Compile, download, online monitoring, and mode-control menu actions are not yet complete; use the CLI workflow above for validated compilation and simulation.

Headless launch verification:

```bash
rsmicro-studio examples/integrated_demo/project.rsmproj \
  --offscreen --verify --run-duration 0.1
```

## 9. Preview a canonical SCADA screen

```bash
rsmicro-scada \
  --project examples/integrated_demo/project.rsmproj \
  --screen overview \
  --role viewer
```

The loader confines paths to the project directory, requires the canonical `rsmicro-scada-screen` schema, verifies declared IDs/names, rejects executable content, and checks every tag against its owning controller.

The current view is intentionally an **offline preview**. Values are marked STALE and writes are disabled for the viewer role because live broker-to-SCADA delivery is not implemented.

Headless verification:

```bash
rsmicro-scada \
  --project examples/integrated_demo/project.rsmproj \
  --screen overview --offscreen --verify --run-duration 0.1
```

Available demo screens:

- `overview`
- `controller_a`
- `controller_b`
- `alarms`
- `trends`

## 10. Run the bounded repository smoke

```bash
PYTHONPATH=src python tools/validate_repository.py --format text
PYTHONPATH=src python tools/run_integrated_demo.py \
  --headless --format json --artifacts-dir build/integrated-smoke
```

This verifies repository contracts and deterministic compile/inspect behavior. It deliberately reports the live node/broker lifecycle, routing/fail-safe behavior, Studio online mode, and SCADA connectivity as not implemented.

## 11. Try the legacy Tk workbench

The preserved PLC ASCII path is independent from the canonical compiler/C core:

```bash
plc-ascii examples/demo_program.json
```

It includes basic ladder editing, local simulation, forcing, and legacy board tooling. Hardware behavior is not established by the canonical host-software tests.

## Troubleshooting

### `RSmicro core library not found`

Run:

```bash
rsmicro native build --clean --release
```

The default build path is discoverable. For a custom path, set `RSMICRO_CORE_LIBRARY` to the exact `.so`, `.dylib`, or `.dll`.

### Qt cannot connect to a display

For CI or SSH verification, add `--offscreen --verify`. For an actual desktop window, run from a graphical session with `DISPLAY`/Wayland configured.

### Windows CTest cannot find a configuration

Use Release consistently:

```powershell
$env:RSMICRO_CMAKE_CONFIG = "Release"
cmake --build build --config Release --parallel
ctest --test-dir build -C Release --output-on-failure
```

### The SCADA screen says disconnected/STALE

That is expected today. Canonical screen loading and rendering work, but live node → broker → SCADA delivery is not implemented. Do not expose RSM Link publicly while it remains unauthenticated and unencrypted.

## Where to go next

- [Current status](current-status.md)
- [Release readiness](release-readiness.md)
- [Program image format](program-image.md)
- [Runtime ABI](runtime-abi.md)
- [Native binding](native-binding.md)
- [Native node status](native-node.md)
