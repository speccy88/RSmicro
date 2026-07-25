# Task 6 baseline

* Starting commit: `878ab72cc067007069a48b0043f8256f32413eff`; working tree clean.
* Environment: Python 3.14.4, Linux 6.12.13 x86_64, GCC 13.3.0.
* Python baseline: `pip install -e ".[dev]"` could not reach setuptools (HTTP 403); `pytest -q` consequently had 12 import/collection errors.
* C baseline: strict shared configure/build succeeded and CTest passed 4/4.
* Generated registries: instruction, C fixtures, and RSM Link registry checks passed; no RSM Link fixture generator exists.
* RSM Link 1.0; runtime ABI 1.0; instruction ABI 1; image format 1.0.
* Existing Link client states were DISCONNECTED, CONNECTING, NEGOTIATING, CONNECTED, DEGRADED, STALE, CLOSED. Tag updates are typed binary messages with runtime IDs, values, sequence/scan and force metadata; generation ownership required broker enforcement.
* Canonical controllers had basic produced/consumed definitions (source/destination UUID, intervals, timeout, hold/substitute fields). SCADA contained unvalidated screens, alarms, historian and metadata placeholders.
* Missing broker information was explicit route quality companions, secure identities, atomic grouped writes, and complete manifest retrieval in the Python client. Task 6 therefore documents local policy roles and non-atomic safe ordering.
* Preserved targets: legacy Python and Tkinter, CircuitPython, MicroPython, Propeller 2/TAQOZ, compiler, native simulator, C runtime, RSM Link, and rsm-node.
