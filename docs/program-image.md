# RSM1 portable program image

RSM1 format 2.0 is little-endian and uses instruction ABI 2. Its fixed header carries magic, versions, sizes, profile version, ABI, section count, controller UUID, deterministic content hash, and CRC32. CRC is corruption detection, not authentication. All fields are decoded with bounded reads rather than native C struct casts.

The descriptor table supplies type, flags, offset, length, entry count, and reserved fields. Required sections are TAG_TABLE, INITIAL_VALUES, TIMER_LAYOUT, COUNTER_LAYOUT, TASK_TABLE, ROUTINE_TABLE, RUNG_TABLE, INSTRUCTION_STREAM, STATE_LAYOUT, PRODUCED_TAGS, CONSUMED_TAGS, DEBUG_MAP, STRING_TABLE, MEMORY_ESTIMATES, RUNTIME_TAGS, and RUNTIME_RUNGS. Inspection rejects bad magic/version/CRC, truncation, overlap, invalid offsets, duplicates, missing sections, and unknown required types.

The instruction stream uses a fixed 12-byte instruction header followed by explicit 8-byte operands. Debug maps preserve runtime-ID-to-UUID/source-path mappings for tags, instructions, routines, and rungs. `--strip-debug` emits an intentionally empty DEBUG_MAP while retaining binary runtime tag/rung sections, so stripped images remain executable but name/UUID convenience lookup is unavailable.

## Portable-runtime metadata

`RUNTIME_TAGS` and `RUNTIME_RUNGS` are fixed-width little-endian metadata for the C engine. The core requires them and never parses JSON. The format-2/ABI-2 transition is explicit: a core that supports ABI 2 rejects incompatible image/bytecode combinations rather than reinterpreting an older image. Canonical JSON/debug sections remain available for tooling when not stripped.
