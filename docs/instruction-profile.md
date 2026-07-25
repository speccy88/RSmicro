# Instruction profile

RSM-LOGIX-CORE-1 version 2.0.0 / instruction ABI 2 / image format 2.0 / runtime ABI 1.2 is profile-driven. JSON-compatible YAML files are schema-constrained; generated Python/C registries and documentation share their opcodes. BOOL is explicit 0/1, DINT is signed 32-bit with faults rather than undefined overflow, and REAL is finite IEEE-754 binary32. TIMER and COUNTER layouts and owned members are in `profile.yaml`.

TON uses monotonic elapsed milliseconds, not nominal scan increments. CTU/CTD are transition instructions and never clamp ACC to PRE. ONS has a unique state slot per compiled source instruction UUID; prescan marks it true to suppress a startup pulse from an already-true rung. RES preserves PRE and clears defined accumulated/status state; CLR is scalar-only. OTE is de-energized in both lifecycle output passes, while timer enable/timing and counter transition state are initialized/reset according to their metadata. Aliases GTE/GEQ and LTE/LEQ produce warnings and serialize as GE/LE.

Every instruction metadata file cites the official Rockwell Automation *Logix 5000 Controllers General Instructions Reference* (1756-RM003). RSmicro defines a bounded subset and its own image/force/fault behavior; citation does not imply full Logix compatibility.
