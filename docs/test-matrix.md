# Test matrix

| Subsystem | Unit | Integration | End-to-end | Linux | macOS configured | Windows configured | Hardware |
|---|---:|---:|---:|---:|---:|---:|---:|
| Project/compiler/migration | Yes | Yes | Demo compile | Yes | Yes | Yes | N/A |
| C runtime/native binding | Yes | Yes | Native demo | Yes | Yes | Yes | UNVERIFIED |
| RSM Link/node | Yes | Yes | Partial | Yes | Yes | Yes | UNVERIFIED |
| Broker/historian/alarms/routes | Yes | Yes | Partial | Yes | Import/test | Import/test | N/A |
| Studio/standalone SCADA | Not present | Not present | Not present | Not present | Not present | Not present | N/A |

Markers are registered in `pyproject.toml`. Hardware tests must only run after explicit target selection and must state their physical prerequisites.
