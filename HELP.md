# PLC ASCII Help

## Purpose

This file is the practical operator guide for the GUI.

Use it when you want to remember:

- what each button does
- which mode to use
- what the monitor is for
- which keyboard shortcuts are available

## Toolbar Buttons

### Step

Runs one offline PLC scan and keeps the resulting values in the local engine.

Use it when:

- you want to debug one scan at a time
- you want to inspect intermediate timer or tag behavior

### Run

Starts repeated offline scans using the configured scan period.

Use it when:

- you want the local simulation to behave like a running PLC

### Stop

Stops the offline simulation.

Behavior:

- if the simulator was running or stepped, it stops and resets boolean flow
- if you press `Stop` again while already stopped, forces are also cleared
- `Reset Integer` controls whether numeric values reset to zero

### Download

Connects to the board if needed, then sends the full current ladder program to
the board runtime.

Use it when:

- you want to update the running ladder on the board
- you are still working in offline edit mode but want to push a new version

### Upload

Connects to the board if needed, then reads the stored program from the target
and loads it into the IDE.

Use it when:

- the board already has a program on it
- you want to continue editing from what is running on the device

### Go Online

Connects to the board if needed, switches the IDE to online mode, and starts
continuous live monitoring automatically.

Use it when:

- you want the ladder colors and monitor to follow the live board state
- you want to debug the running hardware

### Disconnect

Closes the serial connection, stops live monitoring, and returns the IDE to
offline editing mode.

Use it when:

- you are finished with the board
- you want to make offline edits without staying connected

### Connection Indicator

The toolbar shows whether the IDE is currently connected to the board.

It changes to reflect:

- disconnected state
- connected but still offline editing
- active online live monitoring

### Help

Shows the inline shortcut strip and enables hover tooltips for many controls.

### Reset Integer

Controls how `Stop` handles numeric values in offline mode.

When enabled:

- integers and floats reset
- timer and counter accumulators clear

## Top Menus

### File

- `New`: create an empty program
- `Open...`: load a JSON ladder file
- `Save`: save the current program
- `Save As...`: save to a new file
- `Bindings...`: manage I/O bindings

### Runtime

- `Install runtime to CircuitPython...`
- `Download`
- `Upload`
- `Go Online`
- `Disconnect`

### Debug

- `Set Tag`
- `Force Tag`
- `Unforce Tag`
- `Edit Comment`

### Help

- `Documentation`: opens `DOCS.md`
- `README`: opens `README.md`
- `GUI Help`: opens this file

## Ladder Editing

The center ladder view is the main editor. You can:

- insert instructions
- edit instructions
- add or remove rungs
- create branches
- edit rung comments

The renderer also shows live rung power when values are available.

## Monitor Panel

The monitor tree organizes variables by type and lets you inspect runtime data.

Groups:

- Boolean
- Integer
- Float
- Timer
- Counter

You can do all of the following from the monitor:

- add variables
- edit variables
- delete variables
- double-click a value to modify it
- inspect timer and counter members

Examples:

- a boolean double-click toggles it
- an integer or float double-click prompts for a new value
- timer members like `.pre` and `.acc` can be edited directly

## Variable Management

Variables can exist because:

- you declared them explicitly
- the IDE inferred them from ladder usage

Deleting a variable that is used in the program will prompt you before removing
the affected instructions.

Bindings are also removed when the associated variable is deleted.

## Bindings Manager

The bindings manager is where you map ladder tags to external addresses.

Examples:

- `PB` as input on `IO0`
- `LED` as output on `IO2`

Bindings matter most when the runtime is connected to real or simulated I/O.

## Keyboard Shortcuts

These are the shortcuts shown in the GUI help strip:

| Shortcut | Action |
| --- | --- |
| `i` | Insert before |
| `a` | Append after |
| `b` | Branch under / stack lane |
| `r` | New rung after |
| `Shift+R` | New rung before |
| `c` | Edit comment |
| `f` | Force / unforce selected tag |
| `x` | Delete rung or instruction |
| `Enter` | Edit instruction |
| `Left` / `Right` | Move in level / enter branch / leave top branch lane |
| `Up` / `Down` | Move between branch levels |
| `Shift+Up` / `Shift+Down` | Select previous / next rung |
| `Shift+Left` | Select rung number |
| `Shift+Right` | Select first instruction in rung |

## Recommended Workflows

### Local Development

1. Stay in `Offline`.
2. Build the rung logic.
3. Use `Step` and `Run`.
4. Adjust values from the monitor.
5. Save the JSON file.

### Board Development

1. Open the target ladder file.
2. Use `Runtime` -> `Install runtime to CircuitPython...` if the board needs the runtime bundle.
3. Click `Download` to push the current ladder.
4. Click `Go Online` to start live monitoring.
5. Click `Upload` if you want to recover the board program later.
6. Click `Disconnect` when you want to return to offline editing.

## Button Meanings That Often Cause Confusion

### Download vs Upload

- `Download` means IDE to target
- `Upload` means target to IDE

### Go Online vs Disconnect

- `Go Online` starts live monitoring of the board
- `Disconnect` closes the serial port and returns to offline mode

### Offline vs Online

- `Offline` means the desktop engine is running the logic
- `Online` means the target runtime is running the logic and the IDE is watching it

## If Something Looks Wrong

### Ladder Does Not Change Online

Check:

- target is connected
- `Go Online` has been pressed
- the program was downloaded to the target

### Board Does Not Match IDE

Use:

- `Upload` to see what is actually stored on the board
- `Download` to overwrite it with the current IDE program

### Step/Run/Stop Are Not Doing Anything

Those controls only affect the offline simulator.

## Related Files

- `README.md` for quick project orientation
- `DOCS.md` for architecture and protocol details
