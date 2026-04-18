# PLC ASCII

`PLC ASCII` is a Python-first ladder logic workbench inspired by LDmicro's text
presentation and the general workflow of PLC software such as RSLogix 5000.
This first version focuses on a practical MVP:

- Build ladder programs with basic instructions in an ASCII workbench
- Simulate scan cycles locally
- Force tags like a PLC during simulation
- Download the same program to a remote Python runtime
- Use one transport protocol for serial today, with room for Wi-Fi or BLE later
- Keep Raspberry Pi compatibility aligned with CircuitPython style I/O via Blinka

## Current scope

This repository intentionally implements a vertical slice instead of a complete
PLC IDE. The current engine and IDE currently support:

- `XIC` and `XIO` contacts
- `OTE`, `OTL`, and `OTU` outputs
- `TON` timers
- A Tkinter desktop IDE with rung editing and monitor panels
- ASCII ladder rendering with live rung state indicators
- Local simulation
- A JSON-line runtime protocol
- A device runtime with memory and GPIO backend scaffolding

The default launcher now opens a Tkinter GUI. The original shell workbench is
still available as a secondary CLI entry point for debugging and scripting.

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

If you want serial connectivity:

```bash
pip install -e .[serial]
```

## Run the workbench

```bash
plc-ascii
```

Or load the example directly:

```bash
plc-ascii examples/demo_program.json
```

That opens the Tkinter IDE with:

- rung list and rung ordering controls
- instruction editors for conditions and actions
- a live ladder preview pane
- a tag monitor with set/force/unforce controls
- a bindings editor
- local simulation step/run/stop controls
- remote runtime connect/download/snapshot controls

If you want the original shell version:

```bash
plc-ascii-cli examples/demo_program.json
```

## Example workflow

1. Build a ladder program in the GUI by adding rungs, conditions, actions, and bindings.
2. Simulate and debug locally with the monitor panel and the Step/Run/Stop controls.
3. Force tags from the monitor panel like a PLC.
4. Connect to a demo runtime or a serial target from the Remote tab.
5. Download the program and live-view remote snapshots from the same IDE.

## Device runtime

The device runtime is packaged separately in the same repo:

```bash
plc-runtime --demo
```

That starts a simulated device loop on your development machine.

For Raspberry Pi with Blinka later, the intended pattern is:

- Host app stays unchanged
- Transport stays message-compatible
- The runtime swaps from memory I/O to a Blinka GPIO backend

## Protocol notes

The host and runtime speak newline-delimited JSON messages. Example messages:

```json
{"type": "download_program", "program": {"name": "demo", "rungs": []}}
{"type": "force", "tag": "start_pb", "enabled": true, "value": true}
{"type": "snapshot_request"}
```

The runtime responds with acknowledgements and snapshots:

```json
{"type": "ack", "request": "download_program"}
{"type": "snapshot", "mode": "run", "tags": {"start_pb": true}, "rung_power": {"seal_in": true}}
```

## Next steps

- Add parallel branches and more instructions
- Add direct GPIO implementations for Blinka and CircuitPython boards
- Add Wi-Fi and BLE transports
- Add a true CircuitPython serial transport target script
- Add richer live debug tables and rung highlighting overlays
