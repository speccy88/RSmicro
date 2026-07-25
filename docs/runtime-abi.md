# Runtime ABI

The installed C headers are under `rsmicro/`. Runtime ABI **1.2** keeps ABI-major-1 status values, enum values, callback calling conventions, and caller-owned initialization stable. Query the installed library rather than guessing its layout: `rsm_runtime_abi_major/minor`, `rsm_instruction_abi`, `rsm_image_format_major/minor`, `rsm_profile_id`, and `rsm_runtime_object_size` report the supported contract. Bindings must not inspect runtime arena storage.

The ABI requires instruction ABI **2** and portable image format **2.0** for `RSM-LOGIX-CORE-1`; a core rejects older or incompatible images before activation instead of reinterpreting their bytecode. BOOL is normalized `uint8_t`, DINT is signed 32-bit, and REAL is finite IEEE-754 binary32. Composite TIMER/COUNTER data is observed through member access and snapshot callbacks. The runtime structure holds instance-local handles only; it has no shared program state.

## Image admission and control flow

Image validation is a bounded, binary operation: the portable runtime does not parse JSON. It verifies the CRC and all required sections, binary tag/operand metadata, instruction records, state slots, and `RUNTIME_RUNGS`. Rung records are contiguous instruction ranges. Their routine IDs begin at 0, never use `UINT32_MAX`, are nondecreasing with only the same ID or the next ID permitted, and cannot return to an earlier routine; therefore every routine's rungs are contiguous. Rejected images leave any active program unchanged.

Instruction ABI 2 reserves `BRANCH_BEGIN`, `BRANCH_LANE_BEGIN`, `BRANCH_LANE_END`, and `BRANCH_END` as zero-operand control records. Branches are structurally validated, cannot escape a rung, and have a maximum nesting depth of 32.

## ONS migration

ABI 1.2 / instruction ABI 2 makes `ONS` storage explicit: every ONS instruction carries one writable internal BOOL tag operand. A legacy source-model ONS with no operand is migrated by the compiler into a deterministic, compiler-generated hidden `__rsm_ons_storage_*` BOOL tag. This preserves source compatibility while making state visible in the image; legacy ABI-1 zero-operand ONS bytecode and all format-1 images are rejected by ABI-2 runtimes.
