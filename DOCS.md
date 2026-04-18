# PLC ASCII Documentation

## Overview

`PLC ASCII` is a ladder-logic workbench built in Python. It has three main jobs:

1. Let you create and edit a ladder program in a desktop GUI.
2. Let you simulate that program locally with a software PLC scan.
3. Let you send the same program to a remote runtime and watch it execute live.

The project is intentionally small and readable. The goal is to keep the ladder
format, the execution model, and the transport protocol easy to inspect.

## Main Concepts

### Program

A program is stored as JSON and contains:

- `name`
- `runtime_target`
- `rungs`
- `variables`
- `bindings`

The JSON format is designed so it can be:

- edited in the GUI
- saved to disk
- downloaded to a runtime
- uploaded back from a runtime

`runtime_target` stores the selected board type so the IDE knows whether
`Download`, `Upload`, and `Go Online` should talk to CircuitPython or
Propeller2 TAQOZ when the file is opened again.

### Rungs

A rung is a list of ladder elements. Each rung can also have a comment.

Each element is either:

- a `step`
- a `branch`

Examples of steps:

- `XIC`
- `XIO`
- `OTE`
- `OTL`
- `OTU`
- `TON`
- `CTU`
- `CTD`
- `MOV`
- `CLR`
- math and compare instructions

### Variables

Variables define tags and their data type. Supported types include:

- `bool`
- `int`
- `float`
- `timer`
- `counter`

The IDE can infer missing variables from the ladder, but explicit variables are
important because they preserve:

- tag names
- initial values
- timer presets
- counter presets

That is also why `Download` and `Upload` now move the full program, not just the
logic expression.

### Bindings

Bindings connect ladder tags to physical or logical I/O addresses.

Examples:

- `PB -> input -> IO0`
- `LED -> output -> IO2`

The runtime uses bindings to decide:

- which input address to read into a tag
- which output address to write from a tag

## Desktop Architecture

The desktop app has four important layers.

### 1. Program Model

File: `src/plc_ascii/model.py`

This layer defines the data structures for:

- `Program`
- `Rung`
- `Step`
- `Branch`
- `Variable`
- `Binding`

It also validates the ladder structure and instruction arguments.

### 2. Ladder Engine

File: `src/plc_ascii/engine.py`

This is the local PLC execution engine. It:

- stores tag values
- stores forced values
- tracks timers and counters
- executes each rung in scan order
- produces live snapshots and traces

The engine is used in offline mode inside the IDE.

### 3. IDE

File: `src/plc_ascii/ide.py`

The IDE is the main Tkinter GUI. It is responsible for:

- editing rungs and instructions
- showing the ladder preview
- showing the monitor tree
- switching between offline and online views
- connecting to remote runtimes
- downloading and uploading programs
- rendering documentation windows from markdown

### 4. Remote Session and Transports

Files:

- `src/plc_ascii/remote.py`
- `src/plc_ascii/serial_link.py`
- `src/plc_ascii/subprocess_link.py`

`RemoteSession` exposes high-level runtime actions:

- `hello`
- `download_program`
- `upload_program`
- `set_tag`
- `force_tag`
- `bind_tag`
- `request_snapshot`
- `set_mode`

The transport decides how bytes move:

- `SubprocessJsonTransport` starts the bundled demo runtime on the desktop
- `SerialJsonTransport` talks to a hardware target over serial

## Offline vs Online

### Offline

Offline mode means the desktop engine is the active PLC.

Use this mode to:

- build the ladder
- test logic quickly
- add timers and counters
- change monitor values
- run one scan or continuous scans

### Online

Online mode means the IDE is showing a remote runtime snapshot.

Use this mode to:

- connect to the demo runtime
- connect to the CircuitPython board
- monitor real tags
- force and unforce remote values
- download an updated program
- upload the stored program from the target

## Runtime Protocol

The host and runtime communicate using JSON messages over line-oriented serial
or a subprocess pipe.

### Common Messages

| Message | Purpose |
| --- | --- |
| `hello` | Confirms host/runtime communication |
| `snapshot_request` | Requests a live state snapshot |
| `set_tag` | Writes a tag value |
| `force` | Enables or clears a forced tag |
| `run` | Sets runtime mode, usually `run` |

### Download

`Download` sends the full program to the target runtime.

That includes:

- rung comments
- rung structure
- instruction parameters
- variable names
- variable types
- timer presets
- bindings

The current implementation uses chunked transfer so larger programs can move
reliably over the CircuitPython serial console.

For CircuitPython, `Download` can also install the runtime first if the board
does not answer the PLC protocol yet.

### Upload

`Upload` requests the stored program from the target runtime.

The returned program is loaded back into the desktop IDE so you can:

- inspect what is already on the board
- reconnect to an existing device
- continue editing from the hardware state

### Live Snapshot

The host still uses snapshot requests internally to ask for live runtime state,
including:

- tags
- timers
- counters
- forced values
- rung power

This is what drives the online live view in the ladder renderer when `Go
Online` is active.

## CircuitPython Runtime

The CircuitPython workflow adds a board-specific runtime bundle.

Files:

- `src/plc_runtime/circuitpython/runtime.py`
- `src/plc_runtime/circuitpython/plc_runtime_portable.py`
- `src/plc_runtime/circuitpython/plc_runtime_board.py`
- `src/plc_runtime/circuitpython/code.py`

### Why There Is a Separate Portable Runtime

The board runtime needs to run under CircuitPython with a smaller standard
library and a more restrictive serial console environment.

The portable runtime therefore:

- keeps the PLC scan logic lightweight
- stores the ladder program as JSON on the board
- reads board inputs through bindings
- writes board outputs through bindings
- answers host protocol requests over the serial console

### Install Runtime to CircuitPython

The `Install runtime to CircuitPython...` menu action does a board-side setup.
It uploads:

- `code.py`
- `plc_runtime_board.py`
- `plc_runtime_portable.py`
- `plc_runtime_config.json`
- `plc_program.json`

The board then boots directly into the PLC runtime.

If the board reports a read-only filesystem over serial, the installer falls
back to copying the same files to a mounted `CIRCUITPY` volume when one is
available on the host computer.

### Board Configuration

The current tested ESP32 mapping is:

- pushbutton on `IO0`
- LED on `IO2`
- `IO0` treated as active-low with pull-up

Example program:

- `examples/circuitpython_button_led.json`

## Propeller 2 TAQOZ Runtime

The Propeller 2 workflow uses TAQOZ in RAM instead of copying Python files onto
the board filesystem.

Files:

- `src/plc_runtime/propeller2/runtime.py`
- `src/plc_runtime/propeller2/runtime.fth`
- `src/plc_runtime/propeller2/transport.py`

The host now generates TAQOZ source that:

- declares the ladder state in hub RAM
- embeds the full ladder JSON into the TAQOZ runtime for `Upload`
- binds Propeller 2 pins to ladder tags
- answers simple host commands through the TAQOZ console
- executes ladder scans on the Propeller 2 when the IDE requests them online

### Load Runtime to Propeller 2 (RAM)

The `Load Runtime to Propeller 2 (RAM)...` menu action:

- enters TAQOZ over serial
- cold-starts the board into a clean RAM session
- compiles the current ladder into TAQOZ words
- loads the generated `runtime.fth` program into TAQOZ RAM for online control

The current tested setup assumes:

- TAQOZ over the board USB serial link
- onboard LEDs on pins `56` through `63`
- those LEDs are active-low

Example program:

- `examples/propeller2_led56.json`

### Current Limitation

This runtime is intentionally RAM-only for now.

On the tested board, re-entering TAQOZ after closing the serial session triggers
a cold start, which clears the RAM runtime. That means:

- `Download`, `Upload`, and `Go Online` work within one live TAQOZ session
- the current implementation performs scans on demand from the live IDE session
- online force support is not implemented yet for the Propeller 2 target
- persistence across a fresh reconnect will need a later flash or SD solution,
  or a dedicated serial runtime that does not depend on re-entering TAQOZ

## Live View Behavior

The ladder renderer uses current values to color the ladder.

In general:

- green means energized / true / on
- red means false / off for active elements
- muted colors mean inactive structure or labels

When online, the renderer uses the latest remote snapshot. When offline, it
uses the local engine state.

## Monitor Panel

The monitor panel groups values by type:

- Boolean
- Integer
- Float
- Timer
- Counter

You can:

- add variables
- edit variables
- delete variables
- double-click values to change them
- inspect timer members like `.pre`, `.acc`, `.dn`, `.en`, `.tt`

When online, monitor edits go to the remote runtime. When offline, they change
the local engine state.

## Typical Workflows

### Build and Test Locally

1. Create or open a ladder JSON file.
2. Add variables and bindings.
3. Use `Step`, `Run`, and `Stop`.
4. Double-click monitor values to test logic.

### Run on a CircuitPython Board

1. Open the board program.
2. Use `Runtime` -> `Install runtime to CircuitPython...` when the board needs the runtime bundle.
3. Click `Download` after making changes.
4. Click `Go Online` for live monitoring.
5. Use `Upload` if you want to recover the running ladder from the board.
6. Click `Disconnect` to close the serial connection and return to offline mode.

## Important Behavior Notes

### Step, Run, Stop

These are offline-only controls.

- `Step` runs one scan
- `Run` starts repeated scans
- `Stop` ends offline simulation

If already stopped, pressing `Stop` again also clears forces.

### Connection Indicator

The toolbar shows whether the board is:

- disconnected
- connected while still in offline edit mode
- online and actively monitored

### Download

Sends the full current ladder program to the connected target.

### Upload

Reads the target's stored program and replaces the current IDE program with it.

### Go Online

Ensures the serial connection exists, switches the IDE to online mode, and
starts continuous live monitoring automatically.

### Disconnect

Closes the board serial connection, stops live monitoring, and returns the IDE
to offline editing.

## Files You Should Know

| File | Purpose |
| --- | --- |
| `README.md` | Project summary and quick-start |
| `HELP.md` | GUI help and shortcut reference |
| `DOCS.md` | Deeper architecture and runtime documentation |
| `examples/demo_program.json` | Original desktop demo ladder |
| `examples/circuitpython_button_led.json` | ESP32 button-to-LED board demo |

## Limitations

Current limitations include:

- the instruction set is still intentionally small
- the board runtime currently focuses on simple digital I/O
- transports are serial and subprocess only
- the GUI is optimized for a readable MVP, not a full industrial IDE

## Recommended Reading Order

If you are new to the project:

1. Read `README.md`
2. Read `HELP.md`
3. Read this `DOCS.md`
4. Open `examples/circuitpython_button_led.json`
5. Connect to the board and watch the live ladder
