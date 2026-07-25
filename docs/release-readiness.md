# Release readiness

Classification: **READY FOR NATIVE SOFTWARE EXPERIMENTATION**, **NOT READY FOR PRODUCTION INDUSTRIAL CONTROL**, **NOT HARDWARE VALIDATED**, and **NOT SAFETY CERTIFIED**.

The Linux baseline used Python 3.14.4, CMake 3.28.3, GCC 13.3.0, and Clang 17.0.0. Four CTest tests passed. Python installation/testing was blocked by the environment package proxy; Qt was unavailable. Deterministic registry checks, integrated project validation, both controller compilations, and repository validation pass. Sanitizers, wheel/sdist installation, live controller/broker orchestration, Studio, and standalone SCADA remain release blockers for any broader claim.

Supported software includes the canonical model, deterministic compiler/images, C99 core, native node, RSM Link, native binding, broker, historian, alarms, and routes. RSM Link 1.0 has neither authentication nor encryption; use loopback or an isolated trusted network. CRC is not authentication. RSmicro is not safety-rated: emergency stops, overload protection, and protective interlocks must be independent hardware or certified safety systems. Forces can create hazardous motion and alarm acknowledgement does not remove a hazard.

The recommended first physical target is a Linux SBC with virtual I/O first and libgpiod second. Validate safe startup, input/output polarity, monotonic timing, timer/counter behavior, watchdog, force visibility/clearing, failed-download preservation, disconnect fallback, power-cycle persistence, and a supervised long run before considering another target.
