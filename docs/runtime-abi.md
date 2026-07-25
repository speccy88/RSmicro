# Runtime ABI

The installed headers are under `rsmicro/`. BOOL is normalized uint8, DINT is signed 32-bit, and REAL is finite IEEE-754 binary32. ABI 1 uses stable status values and fixed fault/message identifiers. Composite values use member access. The runtime struct contains instance handles but no shared globals. A future binding must treat the public ABI as versioned and must not inspect arena storage.

## Python binding additions (ABI 1.1)

Task 4 adds query-only, static-lifetime ABI functions: `rsm_runtime_abi_major/minor`, `rsm_instruction_abi`, `rsm_image_format_major/minor`, `rsm_profile_id`, `rsm_runtime_object_size`, and stable mode/type/fault-category names. ABI 1.x preserves all Task 3 calls and caller-owned initialization. The object size is queried rather than guessed; enum numeric values and callback calling convention are stable for ABI major 1.
