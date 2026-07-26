# Integrated native demonstration

This checked-in project contains two canonical native-target controllers, five canonical SCADA screens, and a loopback tag-broker configuration whose controller UUIDs are cross-validated against the project.

## Available now

From the repository root:

```bash
rsmicro native build --clean --release
rsmicro validate examples/integrated_demo/project.rsmproj
rsmicro run-native examples/integrated_demo/project.rsmproj \
  --controller controller-a --mode run --duration 0.25 \
  --show-tags --show-diagnostics --format json
```

Open the offline engineering and operator views:

```bash
rsmicro-studio examples/integrated_demo/project.rsmproj
rsmicro-scada --project examples/integrated_demo/project.rsmproj \
  --screen overview --role viewer
```

The SCADA loader resolves each project `{screen_id, name, path}` declaration through one production parser, confines paths to the project, requires the canonical schema, and verifies tag ownership. Its displayed values are intentionally STALE because no live broker is connected.

## Deterministic repository smoke

```bash
PYTHONPATH=src python tools/run_integrated_demo.py \
  --headless --format json --artifacts-dir build/integrated-smoke
```

The smoke validates the repository, compiles each controller twice to separate `.rsm` files, compares their bytes, and inspects each image.

## Not implemented by this demo

The smoke and screenshots do not start or prove:

- a protocol-serving, cyclic `rsm-node`;
- live controller-to-broker tag delivery;
- routing or fail-safe transitions;
- live alarm/historian behavior;
- Studio online/download/mode operations;
- SCADA broker updates or operator writes;
- physical hardware.

All listeners default to loopback. RSmicro is experimental, unauthenticated at the RSM Link layer, and not suitable for production or safety control.
