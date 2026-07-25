# ADR: Caller-owned runtime arena

**Status:** Accepted

## Decision

All mutable storage is deterministically carved from a caller arena; images remain immutable borrowed bytes.

## Consequences

The rule is testable on hosted and freestanding-like C99 targets and keeps platform policy outside the instruction engine.
