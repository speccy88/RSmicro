# Propeller 2 TAQOZ Runtime

This document explains how the Propeller 2 runtime works in this repository, how it is generated, how it talks to the host, what is stored on the board, and why the current design looks the way it does.

The implementation described here is the current code in:

- [src/plc_runtime/propeller2/runtime.py](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/runtime.py)
- [src/plc_runtime/propeller2/runtime.fth](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/runtime.fth)
- [src/plc_runtime/propeller2/transport.py](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/transport.py)

## Overview

The Propeller 2 backend compiles a ladder program into TAQOZ Forth source, sends that source over a serial connection to the board, and then operates the runtime through TAQOZ commands.

At a high level:

1. The host opens the serial port and enters the TAQOZ prompt.
2. Python generates a complete TAQOZ runtime specialized for the current ladder program.
3. The generated source is loaded into RAM only.
4. The runtime initializes its variables, starts a background cog, and waits in `stop` mode.
5. The host uses normal TAQOZ command/response interactions to:
   - say hello
   - download a new runtime
   - upload the current stored ladder program
   - take snapshots
   - switch between `run` and `stop`
   - edit tags, timers, counters, and forces

This design intentionally does not depend on `BACKUP` or `RESTORE`, and it does not currently depend on the custom `PLC.HOST` foreground protocol for host communication.

## Design Goals

The current runtime design is shaped by a few practical goals:

- Keep execution on the Propeller 2 side simple and deterministic.
- Let TAQOZ act as a reliable bootstrap and command shell.
- Run the ladder scan in a dedicated background cog.
- Keep host interaction fast enough for an IDE watch window and online edits.
- Avoid fragile persistence tricks and RAM aliasing problems.
- Preserve a readable mapping from ladder constructs to generated TAQOZ words.

## What The Host Loads

The generated runtime is built from the template in [runtime.fth](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/runtime.fth). That template has placeholders such as:

- `@@DATA_WORDS@@`
- `@@CORE_WORDS@@`
- `@@TIMER_WORDS@@`
- `@@COUNTER_WORDS@@`
- `@@RUNG_WORDS@@`
- `@@SET_WORDS@@`
- `@@HOST_WORDS@@`
- `@@SNAPSHOT_LINES@@`
- `@@UPLOAD_LINES@@`
- `@@INIT_LINES@@`
- `@@RUNTIME_WORDS@@`

`Propeller2Runtime.build_runtime_source()` fills those placeholders with a program-specific TAQOZ runtime.

The final generated source contains:

- storage words for runtime state
- helper words such as `PLC.BOOL`
- one generated word per timer and counter helper
- one generated word per ladder rung
- input and output handling
- force application logic
- online-edit helper words
- snapshot and upload words
- initialization words
- background runtime words for the scan task

The template ends by executing `PLC.START.RUNTIME`, so loading the source also initializes and starts the runtime automatically.

## RAM-Only Runtime

The runtime is RAM-only.

That means:

- every download rebuilds and reloads the runtime into TAQOZ RAM
- power-cycling the board loses the PLC runtime
- there is no flash persistence step in the current implementation

This is deliberate. Earlier approaches that leaned on persistence and more invasive takeover behavior were much less reliable during development and debugging.

## Serial Attach And TAQOZ Entry

The serial attach logic lives in [runtime.py](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/runtime.py).

Important constants:

- `DEFAULT_BAUDRATE = 921600`
- `DEFAULT_SCAN_MS = 1`
- `FALLBACK_BAUDRATES = (921600, 115200)`

### `open_taqoz_console()`

`open_taqoz_console()` tries to enter the TAQOZ prompt at one or more baud rates.

The attach strategy is:

- try the requested baud first
- then try known fallback baud rates
- reset the port if needed
- confirm the `TAQOZ# ` prompt before declaring success

### `TaqozConsole`

`TaqozConsole` is the small serial helper around a pyserial port. It handles:

- entering TAQOZ with reset or a plain carriage return
- reading until the TAQOZ prompt comes back
- sending single commands
- sending source code line by line

The source loader does one important thing: it groups Forth colon definitions into single commands before sending them. That keeps multi-line definitions intact when transmitted to TAQOZ.

## Program Analysis And Compile Context

Before generating TAQOZ code, the runtime builds a `CompileContext`.

This context holds:

- the validated `Program`
- the configured scan period
- the scalar, timer, and counter variable lists
- generated symbol names for all runtime storage
- input and output bindings
- extra scratch symbols used by branches and stateful instructions

### Supported Variable Types

The Propeller 2 runtime currently supports:

- `bool`
- `int`
- `timer`
- `counter`

Unsupported numeric features such as non-integer `float` handling raise a `Propeller2RuntimeError` during code generation.

### Generated Storage Symbols

The generator allocates storage names like:

- `PLCDATA0`
- `PLCDATA1`
- `PLCDATA2`

These are plain TAQOZ `VAR` cells.

This detail matters. During development, other allocation strategies caused real runtime corruption on hardware. The current implementation uses:

- `bytes` for the host line buffer
- `VAR` for scalar cells and internal state

That arrangement proved stable on the board.

## Runtime Memory Model

The generated data section starts with host parser storage:

- `128 bytes PLCHOSTBUF`
- `VAR PLCHOSTLEN`
- `VAR PLCHOSTPTR`
- `VAR PLCHOSTA`
- `VAR PLCHOSTB`
- `VAR PLCHOSTC`

Then it creates one `VAR` cell for every generated runtime symbol.

Those cells back:

- runtime mode
- scan period
- scalar values
- force enable flags
- force override values
- timer fields such as `pre`, `acc`, `dn`, `en`, `tt`
- counter fields such as `pre`, `acc`, `dn`
- branch scratch storage
- edge-detect scratch state for counters

## Ladder Execution Model

The runtime is a cyclic PLC scan.

The generated `PLC.SCAN` word is:

1. `PLC.INPUTS`
2. `PLC.APPLY.FORCES`
3. all generated `PLC.RUNG.n` words
4. `PLC.APPLY.FORCES` again
5. `PLC.OUTPUTS`

That sequence is important.

### Why Forces Are Applied Twice

Forces are applied before rung execution and again after rung execution.

This gives force values priority over ladder logic:

- the first application makes the forced value visible to rung logic
- the second application prevents rung logic from overwriting the forced output/state before outputs are driven

## Inputs And Outputs

### Inputs

`PLC.INPUTS` reads each bound input pin with `PIN@` and stores the value into the corresponding scalar tag.

Most inputs use:

- `0<> PLC.BOOL`

Pins in `DEFAULT_ACTIVE_LOW_OUTPUTS` use inverted logic:

- `0= PLC.BOOL`

### Outputs

`PLC.OUTPUTS` writes bound output pins using `HIGH` or `LOW` depending on the current tag state.

Pins `56..63` are treated as active-low by default:

- if the tag is true, the runtime drives the pin `LOW`
- if the tag is false, the runtime drives the pin `HIGH`

This matches the Propeller 2 board LED wiring expected by the project.

## Rungs And Generated Code

Each ladder rung becomes a word named:

- `PLC.RUNG.0`
- `PLC.RUNG.1`
- and so on

Each rung starts by pushing `1` as the current rung power. Then the generator emits TAQOZ code for each instruction and branch in sequence.

For example:

- contacts read source tags and gate the current power
- coils store the resulting value
- math and move instructions operate on runtime cells
- timers and counters call generated helper words

The generator handles nested branches through temporary branch symbols stored in the compile context.

## Timers

Each timer gets a generated helper word such as:

- `PLC.TON.0`

Timer storage includes:

- `pre`
- `acc`
- `dn`
- `en`
- `tt`

The timer helper:

- stores the enable state
- increments the accumulator by the scan period while enabled
- clamps `acc` to `pre`
- updates `dn`
- updates `tt`
- resets `acc`, `dn`, and `tt` when not enabled

The configured scan period used by the timer is stored in a runtime variable, so timer accumulation is tied to the runtime's `scan_ms`.

## Counters

Counters get generated up/down helper words and state cells for edge detection.

Counter storage includes:

- up-edge scratch
- down-edge scratch
- `pre`
- `acc`
- `dn`

The counter helpers perform edge-sensitive counting and update `dn` when the accumulator meets the preset condition used by the implementation.

## Online Editing Helpers

The runtime generates direct setter words for host-driven edits.

Examples:

- `PLC.SET.0`
- `PLC.FORCE.SET.0`
- `PLC.FORCE.CLEAR.0`
- `PLC.SET.TIMER.PRE.0`
- `PLC.SET.TIMER.ACC.0`
- `PLC.SET.COUNTER.ACC.0`

These words are what the Python transport calls through TAQOZ.

This is one of the key design choices in the current system:

- the board owns the runtime state and scan logic
- the host does not poke raw memory addresses
- the host invokes stable words with values

## Hello, Snapshot, And Upload

The runtime includes three important host-facing words:

- `PLC.HELLO`
- `PLC.SNAPSHOT`
- `PLC.UPLOAD`

### `PLC.HELLO`

`PLC.HELLO` returns a simple version marker:

- `PLC HELLO 2`

The transport uses this to detect whether the Propeller 2 currently has the PLC runtime loaded.

### `PLC.SNAPSHOT`

`PLC.SNAPSHOT` prints a machine-readable dump surrounded by:

- `PLC SNAPSHOT BEGIN`
- `PLC SNAPSHOT END`

Inside that block it prints:

- mode
- scalar variables
- active forces
- timer state
- counter state

The Python transport parses those lines back into a structured snapshot payload.

### `PLC.UPLOAD`

`PLC.UPLOAD` prints the currently loaded ladder program as hex-encoded JSON chunks:

- `PLC CHUNK <index> <hex>`

This allows the host to reconstruct the last loaded logical program, not just the live variable state.

## Why The Program Is Embedded As Hex JSON

The generated runtime stores the host-side `Program` model as serialized JSON turned into hex chunks.

That makes upload simple and robust:

- the board does not need a general JSON encoder
- TAQOZ only has to print known chunk literals
- the host can rebuild the exact ladder program from `PLC.UPLOAD`

## Initialization

`PLC.INIT` sets all runtime state to a defined starting condition.

It initializes:

- scan period
- mode to `stop`
- scalar variables to their configured initial values
- force enable flags to `0`
- force value cells to the current initial value
- timer presets and zeroed timer runtime fields
- counter presets and zeroed counter runtime fields
- counter edge-detect scratch cells

The runtime starts in `stop`, not `run`.

That means downloading a program does not immediately begin scanning. The host must explicitly issue a `run` command.

## Background Scan Execution

The actual background execution lives in the generated runtime words:

- `PLC.RUNNER`
- `PLC.START.COG`
- `PLC.RESTORE.RUNTIME`
- `PLC.START.RUNTIME`

### `PLC.RUNNER`

`PLC.RUNNER` loops forever:

- if mode is `run`, execute `PLC.SCAN`
- wait `scan_ms`
- repeat

### `PLC.START.COG`

`PLC.START.COG`:

1. stops cog 1
2. starts a fresh cog 1
3. waits `5 ms`
4. installs `PLC.RUNNER` into that cog's task slot

### `PLC.RESTORE.RUNTIME`

`PLC.RESTORE.RUNTIME`:

- sets mode to `stop`
- starts the background cog

### `PLC.START.RUNTIME`

`PLC.START.RUNTIME`:

1. runs `PLC.INIT`
2. runs `PLC.RESTORE.RUNTIME`

### Why These Words Are Emitted At The End

This was an important bug fix.

`PLC.RUNNER` must be compiled after `PLC.SCAN` exists. Earlier versions emitted the runtime task words too early, and on real hardware the background scan task failed even though manual `PLC.SCAN` worked.

Placing `@@RUNTIME_WORDS@@` after `PLC.INIT` in the template ensures the runner is compiled against the final `PLC.SCAN`.

## The Generated `PLC.HOST` Protocol

The runtime still generates a custom foreground line protocol:

- `PLC.HOST`
- `PLC.HOST.CMD.HELLO`
- `PLC.HOST.CMD.SNAPSHOT`
- `PLC.HOST.CMD.UPLOAD`
- `PLC.HOST.CMD.RUN`
- `PLC.HOST.CMD.SET`
- `PLC.HOST.CMD.FORCE`
- `PLC.HOST.CMD.TIMER`
- `PLC.HOST.CMD.COUNTER`
- `PLC.HOST.CMD.QUIT`

This protocol uses `!HELLO`, `!VAR`, `!TIMER`, and similar response lines.

### Important Current Status

The Python transport does not currently use `PLC.HOST`.

It is left in the generated runtime, but the working host path uses ordinary TAQOZ command execution instead. This is because the foreground protocol handoff proved unreliable during real hardware testing.

The core issue was that entering the foreground host loop from the prompt was more fragile than expected, while prompt-driven command execution was stable and fast enough once the serial timeout was reduced.

So today:

- `PLC.HOST` exists in the runtime
- the IDE and transport do not rely on it
- prompt-driven TAQOZ control is the supported path

## Host Transport Architecture

The host-side runtime transport is [transport.py](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/transport.py).

Its job is to translate generic remote PLC messages into Propeller 2 specific TAQOZ commands.

### Attach Strategy

`Propeller2Transport.__post_init__()` tries several attach styles:

1. no reset, short attach timeout
2. reset, short serial timeout
3. reset, larger serial timeout

This is a practical robustness measure. Real hardware sometimes responds better to different attach timing depending on the current board state.

### Host Message Handling

The transport implements:

- `hello`
- `download_program_begin`
- `download_program_chunk`
- `download_program_commit`
- `upload_program_begin`
- `upload_program_chunk`
- `upload_program_end`
- `snapshot_request`
- `run`
- `set_tag`
- `force`

### Download Path

Download works like this:

1. accumulate JSON chunks from the host
2. reconstruct a `Program`
3. re-enter TAQOZ with reset
4. send the generated runtime source
5. cache the program structure locally
6. mark mode as `stop`

### Snapshot Path

For snapshots, the transport runs:

- `PLC.SNAPSHOT`

and parses lines such as:

- `PLC MODE 1`
- `PLC VAR 0 1`
- `PLC TIMER 0 1000 37 0 1 1`

into the IDE-facing structured snapshot.

### Run/Stop Path

The transport maps:

- `run` to `PLC.RUN`
- `stop` to `PLC.STOP`

### Scalar Set Path

A scalar write becomes:

- `<value> PLC.SET.<index>`

### Force Path

A force request becomes either:

- `<value> PLC.FORCE.SET.<index>`
- `PLC.FORCE.CLEAR.<index>`

### Timer And Counter Editing

Timer and counter members are edited through generated words such as:

- `PLC.SET.TIMER.PRE.<index>`
- `PLC.SET.COUNTER.ACC.<index>`

The transport resolves tags like `T1.pre` or `C1.acc` to the correct generated word.

## Why Prompt-Driven TAQOZ Was Chosen

The current transport architecture is the result of hardware debugging.

The repo previously moved toward a more dedicated foreground protocol, but real testing exposed several issues:

- protocol entry was fragile
- serial handoff behavior was noisy
- some approaches hid timing and parser problems rather than simplifying them

The current design works better because:

- TAQOZ prompt handling is already stable
- generated runtime words are simple and direct
- failures are easier to inspect manually from the serial console
- host round-trips are fast enough at `921600` baud with a short serial timeout

In real testing, prompt-driven operations such as `set`, `run`, `snapshot`, and `force` were landing around a few tens of milliseconds per round-trip, which is sufficient for the current IDE use case.

## Known Constraints

The current runtime is intentionally narrow.

Important constraints:

- RAM-only, no persistence across reset/power cycle
- only `bool`, `int`, `timer`, and `counter` are supported
- no full REAL/float execution path
- no generic arbitrary memory editing from the host
- no host dependence on `PLC.HOST`
- upload returns the last loaded logical program, not a decompiled runtime

## Important Implementation Lessons

These are the main lessons encoded in the current code:

### 1. Use Simple TAQOZ Storage Primitives

Stable runtime storage came from:

- `bytes` for the host input buffer
- `VAR` for runtime cells

Other allocation strategies caused corruption on real hardware.

### 2. Compile The Background Runner After `PLC.SCAN`

Manual scan execution working does not guarantee the background scan task is valid. The generation order matters.

### 3. Use TAQOZ As The Shell, Not As Something To Replace

Using ordinary prompt-driven command execution turned out to be more reliable than trying to force a full transport takeover.

### 4. Keep The Runtime In `stop` After Download

This makes downloads safer and easier to debug. The host can inspect state before starting scan execution.

### 5. Keep Host Parsing Textual And Explicit

Snapshot and upload output are intentionally text-based and rigidly formatted so the host parser stays simple.

## Typical Runtime Lifecycle

A normal session looks like this:

1. Create `Propeller2Transport`
2. Attach to TAQOZ at `921600` or fallback `115200`
3. Send `hello`
4. Download a program
5. Optionally set or force tags while in `stop`
6. Send `run`
7. Periodically request snapshots
8. Stop, edit, or redownload as needed

## File Responsibilities

### [src/plc_runtime/propeller2/runtime.py](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/runtime.py)

Responsible for:

- validating compile support
- allocating generated symbols
- generating TAQOZ source
- opening TAQOZ serial sessions
- installing the runtime

### [src/plc_runtime/propeller2/runtime.fth](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/runtime.fth)

Responsible for:

- defining the skeleton layout of the generated runtime
- controlling generation order
- ensuring startup executes `PLC.START.RUNTIME`

### [src/plc_runtime/propeller2/transport.py](/Users/fred/Documents/Code/PLC/src/plc_runtime/propeller2/transport.py)

Responsible for:

- mapping generic remote messages to Propeller 2 behavior
- attaching to the serial console robustly
- parsing snapshot/upload output
- issuing TAQOZ commands for online control

## Summary

The Propeller 2 TAQOZ runtime in this repository is a generated, RAM-only PLC runtime that:

- compiles ladder logic into TAQOZ Forth words
- stores PLC state in TAQOZ `VAR` cells
- runs the scan loop in a background cog
- exposes snapshots, upload, and online edit helpers as TAQOZ words
- is controlled from Python through ordinary TAQOZ command/response traffic

That combination turned out to be the most reliable path on real hardware while still staying fast enough for interactive use.
