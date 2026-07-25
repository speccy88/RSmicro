# ADR: Explicit lifecycle scans

**Status:** Accepted

## Decision

Mode transitions invoke dedicated lifecycle state handling, never fake ladder scans.

## Consequences

The rule is testable on hosted and freestanding-like C99 targets and keeps platform policy outside the instruction engine.
