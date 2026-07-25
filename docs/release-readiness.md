# Release readiness

Classification: **READY FOR NATIVE SOFTWARE EXPERIMENTATION**; **NOT READY FOR PRODUCTION INDUSTRIAL CONTROL**; **HARDWARE UNVERIFIED**; **NOT SAFETY CERTIFIED**.

The release contract is RSM-LOGIX-CORE-1 profile **2.0.0**, instruction ABI **2**, image format **2.0**, and runtime ABI **1.2**. Required local evidence is `mypy src/rsmicro`, `ruff check .`, `tools/validate_repository.py`, and `tools/run_integrated_demo.py --headless`; the smoke compiles each controller twice to separate files, compares bytes, and inspects the resulting images.

That smoke does **not** start `rsm-node`, `rsmicro-tagd`, Studio, or standalone SCADA. Live node/broker lifecycle, routing/fail-safe behavior, Studio, and SCADA are therefore **NOT_IMPLEMENTED/out of scope for this evidence**. Do not claim them as passing from the static or compiler gates.

Linux native host execution is the only software platform covered by these local gates. CircuitPython, MicroPython, and Propeller 2/TAQOZ remain preserved legacy targets with physical hardware **UNVERIFIED**. RSM Link has no authentication or encryption; use loopback or an isolated trusted network. CRC is corruption detection, not authentication. Independent safety-rated systems remain required for emergency stops, overload protection, guards, and protective interlocks.
