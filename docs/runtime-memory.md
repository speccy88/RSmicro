# Runtime memory

Call `rsm_runtime_required_memory`, supply an eight-byte-aligned-capable arena of at least that size, then load the same immutable image. The image bytes are retained by read-only reference and must outlive the loaded program. The deterministic arena holds decoded tags, composites, forces, state slots, fault and diagnostics. Scans allocate nothing. Sizing and decoder arithmetic are bounds checked.
