# Legacy semantic differences

The preserved Python engine is not the RSM-LOGIX-CORE-1 semantic authority. Its TON advances by nominal `scan_ms`, does not implement the profile's monotonic elapsed-time/wrap policy, and has weaker preset/state validation. CTU clamps at preset and has a simplified done rule/status model. ONS, RES, explicit prescan/postscan, complete counter CU/CD/OV/UN behavior, and owned-member protections are absent or incomplete (CLR must not substitute for RES).

Legacy arithmetic inherits unlimited Python integers and double precision rather than checked DINT and binary32. Snapshot/live-value upload may couple observation, scan/I/O side effects, and source initial values. Structural state paths may collide. Force overlays and multiple destructive writes lack the profile's explicit scan-order/backing-value rules. Migration therefore emits alias warnings today; behavior-change warnings are reserved where exact affected legacy provenance can be established without false positives.

## Native comparison classification

Native comparisons classify observations as `MATCHES_PROFILE`, `EXPECTED_LEGACY_DIFFERENCE`, `UNEXPECTED_DIFFERENCE`, or `NOT_COMPARABLE`; the legacy engine is never the oracle. Expected differences include monotonic TON timing and first-enable behavior, zero presets, counter status/overflow, ONS state isolation, explicit pre/postscan, RES, fixed-width DINT faults, binary32 REAL rounding, immutable snapshots, force overlays, and source/upload separation. The native simulator does not import or execute the legacy engine.
