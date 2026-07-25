# Migrated examples

These checked-in files are deterministically regenerated from the seven original `examples/*.json` files by `tests/test_rsmicro_foundation.py`. Filenames retain the source stem. Each output's controller UUID appears in its project JSON and report.

| Legacy source | Canonical output | Target | Warnings / lossless status |
|---|---|---|---|
| `examples/circuitpython_button_led.json` | `circuitpython_button_led.rsmproj` | circuitpython | safe-state warning; logic lossless |
| `examples/circuitpython_pico2w.json` | `circuitpython_pico2w.rsmproj` | circuitpython | safe-state warning; logic lossless |
| `examples/demo_program.json` | `demo_program.rsmproj` | circuitpython | undeclared tags inferred and safe-state warning; review required |
| `examples/micropython_pico2w.json` | `micropython_pico2w.rsmproj` | micropython | safe-state warning; logic lossless |
| `examples/propeller2_2leds.json` | `propeller2_2leds.rsmproj` | propeller2 | two safe-state warnings; logic lossless |
| `examples/propeller2_led56.json` | `propeller2_led56.rsmproj` | propeller2 | safe-state warning; logic lossless |
| `examples/propeller2_timers.json` | `propeller2_timers.rsmproj` | propeller2 | two safe-state warnings; logic lossless |

All bindings retain their source addresses. Every target mapping requires physical hardware validation; none was performed here. Exact controller UUIDs, extracted deployment data, and diagnostic details are in each adjacent migration report.
