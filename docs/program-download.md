# Transactional downloads

Downloads use BEGIN, uniquely indexed CHUNK messages, VALIDATE, then ACTIVATE. BEGIN bounds image/chunk sizes and checks profile, ABI, controller identity, and staging availability. Duplicate identical chunks are idempotent; conflicting or out-of-range chunks fail. Validation requires complete ranges, SHA-256, image CRC, `rsm_runtime_validate_image`, memory requirements, profile, ABI, and capabilities, and never replaces the active image.

Activation enters PROGRAM safely, postscans the old image, applies safe outputs, retains it in memory, loads/initializes the validated image, increments generation, invalidates manifests/subscriptions, and emits program change. Failure restores the previous image with safe outputs. ABORT erases staging; disconnects and bounded transfer timeouts eventually abort it. Rollback follows the same safe transition. Persistence across restarts and embedded dual-slot flash are future work.
