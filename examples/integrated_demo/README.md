# Integrated native demonstration

This checked-in project has two native-target controller definitions, data-only SCADA screens, and a tag-broker configuration that is accepted by `rsmicro.scada.configuration.load_config`. It is not evidence that nodes, the broker, Studio, SCADA, historian, alarms, or routing are running.

Run the bounded deterministic smoke from the repository root:

```sh
QT_QPA_PLATFORM=offscreen python tools/run_integrated_demo.py --headless --format json
```

The smoke validates the repository, compiles each controller twice to two separate `.rsm` files, compares their bytes, and inspects each image. Its JSON report labels live node/broker lifecycle, Studio, standalone SCADA, and routing/fail-safe behavior as `NOT_IMPLEMENTED` because it does not launch those processes. All configured listener addresses are loopback. This is experimental software, not production or safety control; hardware is **UNVERIFIED**.
