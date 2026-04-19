# Propeller 2 TAQOZ Runtime Plan

## Goal

Make the Propeller 2 target behave like a real persistent runtime instead of a
RAM-only one-shot loader.

The implementation should:

- persist the generated PLC words with `BACKUP`
- recover them after reset with `RESTORE`
- run the PLC scan loop in a separate cog
- keep the console cog available for host commands and snapshots
- only use `uemit` if normal console I/O proves unreliable

## Runtime Model

Move from:

- reset into TAQOZ
- inject a temporary generated program
- use the same interactive session until power cycle

To:

- reset into fresh ROM TAQOZ
- inject a generated PLC runtime and program dictionary
- persist the dictionary with `BACKUP`
- on reconnect/reset, restore the runtime with `RESTORE`
- restart the PLC task cog and continue using the persisted runtime

## Runtime Words

The generated TAQOZ source should expose a stable PLC control surface:

- `PLC.HELLO`
- `PLC.RUN`
- `PLC.STOP`
- `PLC.SNAPSHOT`
- `PLC.UPLOAD`
- `PLC.SET.*`
- `PLC.INIT`
- `PLC.START.RUNTIME`
- `PLC.RESTORE.RUNTIME`
- `PLC.RUNNER`

The PLC scan loop should run in a dedicated cog via the documented
`NEWCOG` + `TASK W!` pattern.

## Persistence

`Download` should:

1. reset to a clean TAQOZ session
2. load the generated PLC words
3. initialize the runtime
4. persist the resulting image with `BACKUP`

Reconnect should:

1. enter TAQOZ
2. probe for `PLC.HELLO`
3. if missing, attempt `RESTORE`
4. if restored, restart the PLC runtime task cog

Persistence is mainly for the generated words and program image. Dynamic ladder
state does not need to survive reset in the first pass.

## Cog Model

- Cog 0 remains the interactive TAQOZ console used by the host transport.
- A dedicated background cog runs the PLC scan loop.
- Shared PLC state remains in HUB memory.
- Start/stop control is handled through HUB variables rather than by tearing
  down the whole runtime dictionary.

## Serial Behavior

Start with the standard console I/O path.

Only introduce `uemit` / `ukey` vector redirection if testing shows that the
background runtime interferes with prompt handling or serial framing.

## Host Transport Changes

`Propeller2Transport` should be updated to:

- detect `runtime missing` vs `runtime loaded`
- attempt `RESTORE` on reconnect when needed
- stop assuming the runtime is RAM-only
- stop manually scanning on every snapshot once the background cog owns the
  scan loop
- support persisted program upload after reconnect
- support run/stop lifecycle against the background cog runtime

## IDE Integration

Once the runtime is stable, the Propeller 2 target should expose:

- working run/stop control
- upload/download against the persisted runtime
- normal online snapshots

## Scope

Keep the first pass limited to the existing Propeller 2 runtime data types:

- `BOOL`
- `DINT`
- `TIMER`
- `COUNTER`

Do not add `REAL` support in this pass.

## Validation

Validation should include:

- generated runtime source tests
- transport tests with mocked TAQOZ console responses
- hardware verification on the connected Propeller 2 board

