# RSM1 portable program image

RSM1 format 1.0 is little-endian and instruction ABI 1. Its fixed header carries magic, versions, sizes, profile version, ABI, section count, controller UUID, deterministic content hash, and CRC32. CRC is corruption detection, not authentication. All fields are decoded with bounded reads rather than native C struct casts.

The descriptor table supplies type, flags, offset, length, entry count, and reserved fields. Required sections are TAG_TABLE, INITIAL_VALUES, TIMER_LAYOUT, COUNTER_LAYOUT, TASK_TABLE, ROUTINE_TABLE, RUNG_TABLE, INSTRUCTION_STREAM, STATE_LAYOUT, PRODUCED_TAGS, CONSUMED_TAGS, DEBUG_MAP, STRING_TABLE, and MEMORY_ESTIMATES. Inspection rejects bad magic/version/CRC, truncation, overlap, invalid offsets, duplicates, missing sections, and unknown required types.

The instruction stream uses a fixed 12-byte instruction header followed by explicit 8-byte operands. Debug maps preserve UUIDs and source model paths. SHA-256 covers the complete emitted image for tooling; the header content hash covers ordered section payloads.

## Portable-runtime metadata (Task 3)

Image 1.0 now has backward-compatible optional section types 15 (`RUNTIME_TAGS`) and 16 (`RUNTIME_RUNGS`). They provide fixed-width little-endian tag initial/storage records and rung instruction ranges. Existing canonical JSON/debug sections remain unchanged. The C runtime requires these sections so it never parses JSON. Existing version semantics and IEEE CRC-32 are retained; no existing field was reinterpreted.
