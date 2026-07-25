# Instruction profile

RSM-LOGIX-CORE-1 version 1.0.0 / ABI 1 is profile-driven. JSON-compatible YAML files are schema-constrained; generated Python/C registries and documentation share their opcodes. BOOL is explicit 0/1, DINT is signed 32-bit with faults rather than undefined overflow, and REAL is finite IEEE-754 binary32. TIMER and COUNTER layouts and owned members are in `profile.yaml`.

TON uses monotonic elapsed milliseconds, not nominal scan increments. CTU/CTD are transition instructions and never clamp ACC to PRE. ONS has a unique state slot per source instruction UUID. RES preserves PRE and clears defined accumulated/status state; CLR is scalar-only. Aliases GTE/GEQ and LTE/LEQ produce warnings and serialize as GE/LE.
