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
- board runtime download/upload/live monitoring controls
- CircuitPython runtime install for supported serial targets
- Propeller 2 TAQOZ runtime loading for supported serial targets

If you want the original shell version:

```bash
plc-ascii-cli examples/demo_program.json
```

## Example workflow

1. Build a ladder program in the GUI by adding rungs, conditions, actions, and bindings.
2. Simulate and debug locally with the monitor panel and the Step/Run/Stop controls.
3. Force tags from the monitor panel like a PLC.
4. Choose the correct board under `Runtime` -> `Target Board`.
5. For CircuitPython, `Download` can install the runtime first if the board needs it.
6. Use `Download`, `Upload`, and `Go Online` to work with the connected board from the same IDE.
7. Use `Disconnect` to close the serial connection and return to offline editing.

## CircuitPython board workflow

For the ESP32 DevKitC V4 setup tested in this repo:

- Pushbutton input: `IO0` with pull-up and active-low logic
- LED output: `IO2`
- Example program: `examples/circuitpython_button_led.json`

Recommended flow:

1. Open `examples/circuitpython_button_led.json` in the IDE.
2. Confirm `Runtime` -> `Target Board` is set to `CircuitPython`.
3. Click `Download`. If the runtime is not present yet, the IDE can install it first and then send the ladder.
4. Click `Go Online`. If the IDE is not connected yet, it will prompt you to connect.
5. Click `Upload` to read the stored program back from the board.
6. Click `Disconnect` to close the serial connection and return to offline mode.

If CircuitPython reports a read-only filesystem over serial, the installer now
falls back to copying the runtime bundle to the mounted `CIRCUITPY` volume
when one is available.

## Propeller 2 TAQOZ workflow

For the Propeller 2 setup tested in this repo:

- TAQOZ console over `/dev/tty.usbserial-P2EEQZ7`
- TAQOZ console defaults to `921600` baud in the IDE/CLI, with fallback probing for `115200`
- onboard LEDs on `P56` to `P63`
- those LEDs are active-low
- example program: `examples/propeller2_led56.json`

Recommended flow:

1. Open `examples/propeller2_led56.json` in the IDE.
2. Confirm `Runtime` -> `Target Board` is set to `Propeller2 TAQOZ`.
3. Choose `Runtime` -> `Load Runtime to Propeller 2 (RAM)...` if you want to preload the TAQOZ runtime.
4. Click `Go Online`, or use `Download` to push the current ladder and immediately reload the TAQOZ runtime in RAM.
5. Use `Upload` to read the stored ladder JSON back from the board while the same TAQOZ session remains active.
6. Click `Disconnect` when you want to return to offline editing.

Current limitation:

- the Propeller 2 runtime is RAM-only for now
- TAQOZ is used as the bootstrap loader, then the board switches into a dedicated line-framed host loop for online commands
- reconnecting after a reset or fresh serial attach loses the RAM runtime, so a fresh `Download` is still the normal recovery path
- scalar online set/force support is available inside one live session; timer and counter live-edit behavior still needs more hardware validation

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
