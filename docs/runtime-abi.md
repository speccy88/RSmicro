# Runtime ABI

The installed headers are under `rsmicro/`. BOOL is normalized uint8, DINT is signed 32-bit, and REAL is finite IEEE-754 binary32. ABI 1 uses stable status values and fixed fault/message identifiers. Composite values use member access. The runtime struct contains instance handles but no shared globals. A future binding must treat the public ABI as versioned and must not inspect arena storage.
