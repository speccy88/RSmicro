# Integrated native demonstration

This deterministic example joins two native deployments, broker-mediated produced/consumed routing, quality companion tags, ten alarm definitions, twelve historian definitions, and five data-only SCADA screens. Controller A covers all 24 mandatory RSM-LOGIX-CORE-1 instructions. Controller B's `RemoteLamp` rung requires the consumed permit, good quality, no stale/bad indication, and local enable; loss of the source substitutes `false` before setting the companion stale state.

Run the bounded verification from the repository root:

```sh
QT_QPA_PLATFORM=offscreen python tools/run_integrated_demo.py --headless --format json
```

The current tool verifies static integration, deterministic compilation, and image inspection. Live multi-process lifecycle, Qt Studio, and standalone Qt SCADA verification are explicitly reported as future work rather than reported as passing. All listeners use ephemeral or loopback ports. This is a simulation example, not production or safety control.
