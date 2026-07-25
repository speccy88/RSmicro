# Alarms

Conditions are BOOL_TRUE, BOOL_FALSE, HIGH, HIGH_HIGH, LOW, LOW_LOW, BAD_QUALITY and STALE_QUALITY. The deterministic lifecycle is NORMAL → PENDING_ACTIVE → ACTIVE_UNACKNOWLEDGED → ACTIVE_ACKNOWLEDGED, with PENDING_RETURN and RETURNED_UNACKNOWLEDGED preserving acknowledgement obligations. Delays use monotonic time; records use UTC. High/low hysteresis applies on clear. Acknowledgements are idempotent at the settled state and reject stale versions. This is single-broker persistence, not redundant SCADA or safety certification.
