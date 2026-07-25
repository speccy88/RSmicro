# ADR: C99 canonical runtime

**Status:** Accepted

## Decision

The portable standard-C engine is canonical; legacy engines remain during migration.

## Consequences

The rule is testable on hosted and freestanding-like C99 targets and keeps platform policy outside the instruction engine.
