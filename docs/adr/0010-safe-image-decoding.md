# ADR: Safe image decoding

**Status:** Accepted

## Decision

Fields are byte-decoded with bounds checks; no packed casts or JSON parser are used.

## Consequences

The rule is testable on hosted and freestanding-like C99 targets and keeps platform policy outside the instruction engine.
